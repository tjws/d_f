<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import SidebarCustomerList from '../components/sidebar/SidebarCustomerList.vue'
import SidebarChatPanel from '../components/sidebar/SidebarChatPanel.vue'
import SidebarContextPanel from '../components/sidebar/SidebarContextPanel.vue'
import SidebarPlanningPanel from '../components/sidebar/SidebarPlanningPanel.vue'
import KnowledgeSearchPanel from '../components/sidebar/KnowledgeSearchPanel.vue'
import SidebarAgentPanel from '../components/sidebar/SidebarAgentPanel.vue'
import { listCustomers } from '../api/customers'
import { listChatMessages, createMockChatMessage } from '../api/chatMessages'
import { syncSidebarCustomer } from '../api/sidebarSync'
import { emitMockCallback } from '../api/wecom'
import { listTimelineEvents } from '../api/timelineEvents'
import { listStudents } from '../api/students'
import { listCustomerProfiles, confirmCustomerProfile } from '../api/customerProfiles'
import { listCustomerTags, confirmCustomerTag, rejectCustomerTag } from '../api/tags'
import { listScheduleSuggestions, updateScheduleSuggestion, confirmScheduleSuggestion, listSchedules, completeSchedule, cancelSchedule } from '../api/schedules'
import type { ScheduleCompletion } from '../types/schedule'
import { listAISuggestions, updateAISuggestion, acceptAISuggestion, rejectAISuggestion } from '../api/aiSuggestions'
import { runAIWorkflow, getAIWorkflowRun, streamAIWorkflowRun } from '../api/aiWorkflow'
import { controlSalesAgent, getSalesAgentRun, retrySalesAgent, runSalesAgent, submitSalesAgentFeedback } from '../api/agent'
import type { Customer } from '../types/customer'
import type { ChatMessage, ChatMessageCreate } from '../types/chatMessage'
import type { CustomerProfile } from '../types/customerProfile'
import type { AISuggestion, AISuggestionUpdate } from '../types/aiSuggestion'
import type { TimelineEvent } from '../types/timelineEvent'
import type { Student } from '../types/student'
import type { CustomerTag } from '../types/tag'
import type { Schedule } from '../types/schedule'
import type { AgentControlPayload, AgentExecutionMode, AgentFeedbackAction, AgentTask, SalesAgentResponse } from '../types/agent'

const customers = ref<Customer[]>([])
const selectedId = ref<number | null>(null)
const messages = ref<ChatMessage[]>([])
const profiles = ref<CustomerProfile[]>([])
const suggestions = ref<AISuggestion[]>([])
const timelineEvents = ref<TimelineEvent[]>([])
const students = ref<Student[]>([])
const tags = ref<CustomerTag[]>([])
const scheduleSuggestions = ref<AISuggestion[]>([])
const schedules = ref<Schedule[]>([])
const planningError = ref('')
const loadingCustomers = ref(false)
const sending = ref(false)
const workflowBusy = ref(false)
const error = ref('')
const chatError = ref('')
const notice = ref('')
const composerDraft = ref('')
const composerSuggestionId = ref<number | null>(null)
const agentResult = ref<SalesAgentResponse | null>(null)
const agentError = ref('')
const selectedCustomer = computed(() => customers.value.find((item) => item.id === selectedId.value) ?? null)
const latestProfile = computed(() => profiles.value[0] ?? null)
let refreshTimer: number | undefined
const lastMessageId = ref(0)
const lastTimelineId = ref(0)
let syncInFlight = false

async function loadCustomers(): Promise<void> {
  loadingCustomers.value = true; error.value = ''
  try { const response = await listCustomers({ page: 1, page_size: 100 }); customers.value = response.items; if (selectedId.value === null && customers.value[0]) selectedId.value = customers.value[0].id } catch (reason) { error.value = reason instanceof Error ? reason.message : '客户列表加载失败' } finally { loadingCustomers.value = false }
}

async function loadCustomerData(): Promise<void> {
  if (selectedId.value === null) return
  const customerId = selectedId.value; chatError.value = ''; notice.value = ''
  planningError.value = ''
  const results = await Promise.allSettled([listChatMessages(customerId), listCustomerProfiles(customerId), listAISuggestions(customerId), listTimelineEvents(customerId), listStudents(customerId), listCustomerTags(customerId), listScheduleSuggestions(customerId), listSchedules(customerId)])
  if (results[0].status === 'fulfilled') { messages.value = results[0].value; lastMessageId.value = Math.max(0, ...messages.value.map((item) => item.id)) } else chatError.value = '聊天记录加载失败'
  if (results[1].status === 'fulfilled') profiles.value = results[1].value
  if (results[2].status === 'fulfilled') suggestions.value = results[2].value.filter((item) => item.suggestion_type === 'reply')
  if (results[3].status === 'fulfilled') { timelineEvents.value = results[3].value; lastTimelineId.value = Math.max(0, ...timelineEvents.value.map((item) => item.id)) }
  if (results[4].status === 'fulfilled') students.value = results[4].value
  if (results[5].status === 'fulfilled') tags.value = results[5].value
  if (results[6].status === 'fulfilled') scheduleSuggestions.value = results[6].value
  if (results[7].status === 'fulfilled') schedules.value = results[7].value
  if ([results[5], results[6], results[7]].some((result) => result.status === 'rejected')) planningError.value = '标签或日程数据加载失败'
}

async function selectCustomer(customerId: number): Promise<void> { selectedId.value = customerId; composerDraft.value = ''; composerSuggestionId.value = null; await loadCustomerData() }
async function syncSidebarIncremental(): Promise<void> {
  if (selectedId.value === null || syncInFlight) return
  syncInFlight = true
  try {
    const result = await syncSidebarCustomer(selectedId.value, lastMessageId.value, lastTimelineId.value)
    if (result.messages.length > 0) messages.value = [...result.messages, ...messages.value].sort((a, b) => b.id - a.id)
    if (result.timeline_events.length > 0) timelineEvents.value = [...result.timeline_events, ...timelineEvents.value].sort((a, b) => b.id - a.id)
    lastMessageId.value = result.next_message_id
    lastTimelineId.value = result.next_timeline_id
  } catch (reason) {
    chatError.value = reason instanceof Error ? reason.message : '侧边栏增量同步失败'
  } finally { syncInFlight = false }
}

async function waitForAgentRun(
  task: AgentTask,
  runId: number,
  initial: SalesAgentResponse,
): Promise<SalesAgentResponse> {
  let latest = initial
  try {
    const terminal = await streamAIWorkflowRun(selectedId.value!, runId, (update) => {
      latest = { ...latest, workflow: update }
    })
    latest = task === 'comprehensive'
      ? await getSalesAgentRun(selectedId.value!, runId)
      : { ...latest, workflow: terminal }
  } catch {
    // SSE 被旧代理中断时保留轮询回退，避免侧边栏失去任务结果。
    for (let i = 0; i < 20; i += 1) {
      await new Promise((resolve) => setTimeout(resolve, 500))
      latest = task === 'comprehensive'
        ? await getSalesAgentRun(selectedId.value!, runId)
        : { ...latest, workflow: await getAIWorkflowRun(selectedId.value!, runId) }
      if (latest.workflow.status !== 'queued' && latest.workflow.status !== 'running') break
    }
  }
  return latest
}

async function waitForWorkflowRun(runId: number): Promise<import('../types/aiWorkflow').AIWorkflowRun> {
  try {
    return await streamAIWorkflowRun(selectedId.value!, runId)
  } catch {
    // 普通工作流也保留短轮询回退，兼容未关闭缓冲的旧代理。
    for (let i = 0; i < 20; i += 1) {
      await new Promise((resolve) => setTimeout(resolve, 500))
      const current = await getAIWorkflowRun(selectedId.value!, runId)
      if (current.status !== 'queued' && current.status !== 'running') return current
    }
  }
  throw new Error('AI 任务仍在处理中，请稍后刷新页面查看结果')
}

async function runSidebarWorkflow(goal: 'tag' | 'schedule'): Promise<void> {
  if (selectedId.value === null) return
  workflowBusy.value = true
  planningError.value = ''
  try {
    let result = await runAIWorkflow(selectedId.value, goal)
    if ((result.status === 'queued' || result.status === 'running') && result.run_id) {
      result = await waitForWorkflowRun(result.run_id)
    }
    if (result.status === 'failed') throw new Error(result.error || 'AI 工作流失败')
    await loadCustomerData()
    notice.value = goal === 'tag'
      ? '标签建议已生成，请人工确认。'
      : '日程建议已生成，请人工编辑并确认。'
  } catch (reason) {
    planningError.value = reason instanceof Error ? reason.message : 'AI 工作流失败'
  } finally {
    workflowBusy.value = false
  }
}

async function runAgent(task: AgentTask, instruction: string, executionMode: AgentExecutionMode): Promise<void> {
  if (selectedId.value === null) return
  workflowBusy.value = true; agentError.value = ''
  try {
    const result = await runSalesAgent(selectedId.value, { task, instruction: instruction || undefined, execution_mode: executionMode })
    agentResult.value = result
    if ((result.workflow.status === 'queued' || result.workflow.status === 'running') && result.workflow.run_id) {
      agentResult.value = await waitForAgentRun(task, result.workflow.run_id, result)
    }
    await loadCustomerData()
  } catch (reason) {
    agentError.value = reason instanceof Error ? reason.message : 'Agent 执行失败'
  } finally { workflowBusy.value = false }
}
async function controlAgent(runId: number, payload: AgentControlPayload): Promise<void> {
  if (selectedId.value === null) return
  workflowBusy.value = true; agentError.value = ''
  try {
    agentResult.value = await controlSalesAgent(selectedId.value, runId, payload)
    const currentRunId = agentResult.value.workflow.run_id
    if ((agentResult.value.workflow.status === 'queued' || agentResult.value.workflow.status === 'running') && currentRunId) {
      agentResult.value = await waitForAgentRun('comprehensive', currentRunId, agentResult.value)
    }
    if (agentResult.value.workflow.status === 'waiting_human') await loadCustomerData()
  } catch (reason) {
    agentError.value = reason instanceof Error ? reason.message : 'Agent 控制失败'
  } finally { workflowBusy.value = false }
}
async function retryAgent(runId: number): Promise<void> {
  if (selectedId.value === null) return
  workflowBusy.value = true; agentError.value = ''
  try {
    agentResult.value = await retrySalesAgent(selectedId.value, runId, true)
    if ((agentResult.value.workflow.status === 'queued' || agentResult.value.workflow.status === 'running') && agentResult.value.workflow.run_id) {
      agentResult.value = await waitForAgentRun('comprehensive', agentResult.value.workflow.run_id, agentResult.value)
      await loadCustomerData()
    }
  } catch (reason) {
    agentError.value = reason instanceof Error ? reason.message : 'Agent 重试失败'
  } finally { workflowBusy.value = false }
}
async function submitAgentFeedback(runId: number, action: AgentFeedbackAction): Promise<void> {
  if (selectedId.value === null) return
  try {
    await submitSalesAgentFeedback(selectedId.value, runId, { action })
    notice.value = 'Agent 反馈已记录，感谢你的纠正。'
  } catch (reason) {
    agentError.value = reason instanceof Error ? reason.message : 'Agent 反馈提交失败'
  }
}
async function sendMessage(payload: ChatMessageCreate): Promise<void> { if (selectedId.value === null) return; sending.value = true; chatError.value = ''; try { if (payload.direction === 'inbound') { await emitMockCallback({ ...payload, event_id: `sidebar-event-${Date.now()}`, event_type: 'chat_message', userid: 'current-user', customer_id: selectedId.value }) } else { await createMockChatMessage(selectedId.value, payload) }; composerDraft.value = ''; composerSuggestionId.value = null; await loadCustomerData() } catch (reason) { chatError.value = reason instanceof Error ? reason.message : '消息写入失败' } finally { sending.value = false } }
async function editSuggestion(id: number, payload: AISuggestionUpdate): Promise<void> { if (selectedId.value === null) return; try { await updateAISuggestion(selectedId.value, id, payload); await loadCustomerData(); notice.value = '回复建议已保存人工编辑。' } catch (reason) { error.value = reason instanceof Error ? reason.message : '建议编辑失败' } }
function useSuggestion(id: number, text: string): void { composerDraft.value = text; composerSuggestionId.value = id; notice.value = '建议已放入聊天框，请人工检查后发送。' }
async function generateReply(): Promise<void> { if (selectedId.value === null) return; workflowBusy.value = true; error.value = ''; notice.value = ''; try { const result = await runAIWorkflow(selectedId.value, 'reply'); if ((result.status === 'queued' || result.status === 'running') && result.run_id) { const terminal = await waitForWorkflowRun(result.run_id); notice.value = terminal.next_action === 'confirm_profile' ? '请先确认客户画像。' : 'AI 回复建议已生成，请人工确认。' } else { notice.value = result.next_action === 'confirm_profile' ? '请先确认客户画像。' : 'AI 回复建议已生成，请人工确认。' } await loadCustomerData() } catch (reason) { error.value = reason instanceof Error ? reason.message : 'AI 工作流失败' } finally { workflowBusy.value = false } }
async function confirmProfile(id: number): Promise<void> { if (selectedId.value === null) return; await confirmCustomerProfile(selectedId.value, id); await loadCustomerData(); notice.value = '画像已人工确认。' }
async function acceptSuggestion(id: number): Promise<void> { if (selectedId.value === null) return; await acceptAISuggestion(selectedId.value, id); await loadCustomerData(); notice.value = '回复建议已接受，请人工发送。' }
async function rejectSuggestion(id: number): Promise<void> { if (selectedId.value === null) return; await rejectAISuggestion(selectedId.value, id); await loadCustomerData(); notice.value = '回复建议已拒绝。' }
async function generateTags(): Promise<void> { await runSidebarWorkflow('tag') }
async function confirmTag(id: number): Promise<void> { if (selectedId.value === null) return; try { await confirmCustomerTag(selectedId.value, id); await loadCustomerData(); notice.value = '标签已确认。' } catch (reason) { planningError.value = reason instanceof Error ? reason.message : '标签确认失败' } }
async function rejectTag(id: number): Promise<void> { if (selectedId.value === null) return; try { await rejectCustomerTag(selectedId.value, id); await loadCustomerData(); notice.value = '标签已拒绝。' } catch (reason) { planningError.value = reason instanceof Error ? reason.message : '标签拒绝失败' } }
async function generateSchedule(): Promise<void> { await runSidebarWorkflow('schedule') }
async function editSchedule(id: number, payload: AISuggestionUpdate): Promise<void> { if (selectedId.value === null) return; try { await updateScheduleSuggestion(selectedId.value, id, payload); await loadCustomerData(); notice.value = '日程建议已保存编辑。' } catch (reason) { planningError.value = reason instanceof Error ? reason.message : '日程编辑失败' } }
async function confirmSchedule(id: number): Promise<void> { if (selectedId.value === null) return; try { await confirmScheduleSuggestion(selectedId.value, id); await loadCustomerData(); notice.value = '正式日程已创建。' } catch (reason) { planningError.value = reason instanceof Error ? reason.message : '日程确认失败' } }
async function completeScheduleItem(id: number, payload: ScheduleCompletion): Promise<void> { if (selectedId.value === null) return; try { await completeSchedule(selectedId.value, id, payload); await loadCustomerData() } catch (reason) { planningError.value = reason instanceof Error ? reason.message : '日程完成失败' } }
async function cancelScheduleItem(id: number): Promise<void> { if (selectedId.value === null) return; try { await cancelSchedule(selectedId.value, id); await loadCustomerData() } catch (reason) { planningError.value = reason instanceof Error ? reason.message : '日程取消失败' } }

onMounted(async () => {
  await loadCustomers()
  await loadCustomerData()
  // Mock 侧边栏只拉取游标之后的数据，避免每 8 秒重复下载完整历史。
  refreshTimer = window.setInterval(() => { void syncSidebarIncremental() }, 8000)
})
onBeforeUnmount(() => { if (refreshTimer !== undefined) window.clearInterval(refreshTimer) })
</script>

<template>
  <main class="sidebar-page">
    <header class="page-header">
      <div class="simulation-title"><span class="wecom-mark">✦</span><div><p class="eyebrow">Local WeCom Simulation</p><h1>企业微信会话工作台</h1><p>本地模拟客户会话、人工发送与 AI 辅助决策。</p></div></div>
      <div class="mode-badge"><i /> 本地 Mock · 不连接真实企业微信</div>
    </header>
    <p v-if="error" class="error">{{ error }}</p>
    <p class="sync-hint"><span>●</span> 会话数据每 8 秒自动同步 · AI 仅提供草稿，发送前始终由人工确认</p>
    <section class="sidebar-frame" aria-label="本地企业微信侧边栏模拟">
      <div class="sidebar-grid">
        <SidebarCustomerList :customers="customers" :selected-id="selectedId" :loading="loadingCustomers" @select="selectCustomer" />
        <SidebarChatPanel :messages="messages" :error="chatError" :sending="sending" :suggested-draft="composerDraft" :suggested-suggestion-id="composerSuggestionId" @send="sendMessage" />
        <div class="sidebar-right-column"><SidebarAgentPanel :customer-id="selectedId" :result="agentResult" :busy="workflowBusy" :error="agentError" @run="runAgent" @control="controlAgent" @retry="retryAgent" @feedback="submitAgentFeedback" /><SidebarContextPanel :customer="selectedCustomer" :profile="latestProfile" :students="students" :suggestions="suggestions" :timeline-events="timelineEvents" :busy="workflowBusy" :notice="notice" :error="error" @run="generateReply" @confirm-profile="confirmProfile" @edit="editSuggestion" @use-suggestion="useSuggestion" @accept="acceptSuggestion" @reject="rejectSuggestion" /><SidebarPlanningPanel :tags="tags" :schedule-suggestions="scheduleSuggestions" :schedules="schedules" :busy="workflowBusy" :error="planningError" @generate-tags="generateTags" @confirm-tag="confirmTag" @reject-tag="rejectTag" @generate-schedule="generateSchedule" @edit-schedule="editSchedule" @confirm-schedule="confirmSchedule" @complete-schedule="completeScheduleItem" @cancel-schedule="cancelScheduleItem" /><KnowledgeSearchPanel /></div>
      </div>
    </section>
  </main>
</template>

<style scoped>
.sidebar-page { min-height: 100vh; padding: 28px clamp(16px, 4vw, 60px) 52px; color: #1f2937; background: radial-gradient(circle at 50% -20%, #dce9ff 0, transparent 36%), #f1f4f8; }.page-header { display: flex; align-items: center; justify-content: space-between; gap: 20px; max-width: 1500px; margin: 0 auto 16px; }.simulation-title { display: flex; align-items: center; gap: 13px; }.wecom-mark { display: grid; width: 42px; height: 42px; place-items: center; border-radius: 14px; color: white; background: linear-gradient(135deg, #07c160, #15b8d5); box-shadow: 0 9px 20px rgb(7 193 96 / 25%); font-size: 21px; }.eyebrow { margin: 0 0 5px; color: #2563eb; font-size: 11px; font-weight: 800; letter-spacing: .13em; }.page-header h1 { margin: 0; font-size: clamp(25px, 3.5vw, 36px); }.page-header p:last-child { margin: 4px 0 0; color: #64748b; }.mode-badge { display: inline-flex; align-items: center; gap: 7px; padding: 9px 12px; border: 1px solid #b7e8cb; border-radius: 999px; color: #16774a; background: #f1fcf5; font-size: 12px; font-weight: 700; }.mode-badge i { width: 7px; height: 7px; border-radius: 50%; background: #07c160; }.sync-hint { display: flex; gap: 7px; max-width: 1500px; margin: 0 auto 12px; color: #718096; font-size: 12px; }.sync-hint span { color: #07c160; }.sidebar-frame { max-width: 1500px; min-height: min(760px, calc(100vh - 185px)); margin: 0 auto; overflow: hidden; border: 1px solid #d8dee8; border-radius: 18px; background: #fff; box-shadow: 0 24px 70px rgb(33 46 68 / 15%); }.sidebar-grid { display: grid; grid-template-columns: 256px minmax(400px, 1fr) 354px; height: min(760px, calc(100vh - 185px)); min-height: 620px; }.sidebar-right-column { display: grid; align-content: start; gap: 12px; overflow-y: auto; padding: 14px; background: #f6f7f9; }.error { max-width: 1500px; margin: 10px auto; color: #b91c1c; }
:deep(.sidebar-frame > .sidebar-grid > .customer-list) { overflow-y: auto; padding: 14px 10px; border-right: 1px solid #e5e9ef; border-radius: 0; background: #f8f9fb; }.sidebar-frame :deep(.chat-panel) { min-height: 0; height: 100%; border-radius: 0; background: #f5f5f5; }.sidebar-frame :deep(.sidebar-right-column .panel) { border: 1px solid #e1e6ed; border-radius: 12px; background: white; box-shadow: 0 4px 12px rgb(15 23 42 / 4%); }
@media (max-width: 1080px) { .sidebar-frame { overflow: visible; }.sidebar-grid { grid-template-columns: 230px minmax(300px, 1fr); height: auto; }.sidebar-right-column { grid-column: 1 / -1; grid-template-columns: repeat(2, minmax(0, 1fr)); overflow: visible; }.sidebar-frame :deep(.chat-panel) { min-height: 620px; } }@media (max-width: 700px) { .sidebar-page { padding: 18px 12px 32px; }.page-header { align-items: flex-start; flex-direction: column; }.sidebar-grid, .sidebar-right-column { grid-template-columns: 1fr; }.sidebar-right-column { padding: 12px; }.sidebar-frame { border-radius: 14px; }.sidebar-frame :deep(.customer-list) { max-height: 260px; border-right: 0; border-bottom: 1px solid #e5e9ef; } }
</style>
