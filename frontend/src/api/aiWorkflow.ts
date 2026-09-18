import { apiRequest } from './http'
import type { AIWorkflowGoal, AIWorkflowRun } from '../types/aiWorkflow'

export function runAIWorkflow(
  customerId: number,
  goal: AIWorkflowGoal = 'reply',
  idempotencyKey?: string,
): Promise<AIWorkflowRun> {
  return apiRequest<AIWorkflowRun>(
    `/customers/${customerId}/ai-workflow`,
    { method: 'POST', body: JSON.stringify({ goal, ...(idempotencyKey ? { idempotency_key: idempotencyKey } : {}) }) },
  )
}

export function getAIWorkflowRun(
  customerId: number,
  runId: number,
): Promise<AIWorkflowRun> {
  return apiRequest<AIWorkflowRun>(
    `/customers/${customerId}/ai-workflow/${runId}`,
  )
}

export function retryAIWorkflow(
  customerId: number,
  runId: number,
  confirm = true,
): Promise<AIWorkflowRun> {
  return apiRequest<AIWorkflowRun>(
    `/customers/${customerId}/ai-workflow/${runId}/retry`,
    { method: 'POST', body: JSON.stringify({ confirm }) },
  )
}

/**
 * 使用 fetch 读取 SSE，而不是原生 EventSource：这样可以继续携带 Bearer 鉴权头。
 * 回调只接收任务状态，不接收聊天正文或模型原始输出。
 */
export async function streamAIWorkflowRun(
  customerId: number,
  runId: number,
  onUpdate?: (run: AIWorkflowRun) => void,
): Promise<AIWorkflowRun> {
  const accessToken = sessionStorage.getItem('access_token')
  const response = await fetch(`${import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'}/customers/${customerId}/ai-workflow/${runId}/events`, {
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
  })
  if (!response.ok || !response.body) {
    throw new Error(`SSE request failed: ${response.status}`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let finalRun: AIWorkflowRun | null = null

  const handleFrame = (frame: string): void => {
    const eventName = frame.match(/^event:\s*(.+)$/m)?.[1]?.trim()
    const dataLine = frame.match(/^data:\s*(.+)$/m)?.[1]
    if (!dataLine) return
    if (eventName === 'timeout') throw new Error('AI 任务推送超时，请稍后刷新查看结果')
    const run = JSON.parse(dataLine) as AIWorkflowRun
    onUpdate?.(run)
    if (eventName === 'done') finalRun = run
  }

  while (true) {
    const { value, done } = await reader.read()
    buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done })
    const frames = buffer.split('\n\n')
    buffer = frames.pop() ?? ''
    frames.filter((frame) => frame.trim()).forEach(handleFrame)
    if (done) break
  }
  if (!finalRun) throw new Error('AI 任务推送提前结束，请稍后刷新查看结果')
  return finalRun
}
