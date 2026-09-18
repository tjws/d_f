<script setup lang="ts">
import { ref, watch } from 'vue'
import type { AgentControlPayload, AgentExecutionMode, AgentFeedbackAction, AgentTask, SalesAgentResponse } from '../../types/agent'

const props = defineProps<{
  customerId: number | null
  result?: SalesAgentResponse | null
  busy?: boolean
  error?: string
}>()

const emit = defineEmits<{
  run: [task: AgentTask, instruction: string, executionMode: AgentExecutionMode]
  control: [runId: number, payload: AgentControlPayload]
  retry: [runId: number]
  feedback: [runId: number, action: AgentFeedbackAction]
}>()
const task = ref<AgentTask>('auto')
const instruction = ref('')
const executionMode = ref<AgentExecutionMode>('complete')
const skipTools = ref<string[]>([])
const correctionNote = ref('')
const feedbackSent = ref(false)
watch(() => props.result?.workflow.run_id, () => { feedbackSent.value = false })

const toolOptions = [
  { value: 'knowledge.search', label: '知识库' },
  { value: 'customer_profile.read_confirmed', label: '已确认画像' },
  { value: 'orders.list', label: '订单资料' },
  { value: 'tags.analyze', label: '客户标签' },
  { value: 'course_openings.read', label: '课程开班' },
]

function submit(): void {
  if (props.customerId === null || props.busy) return
  emit('run', task.value, instruction.value.trim(), executionMode.value)
}

function control(action: AgentControlPayload['action'], stepLimit = 1): void {
  const runId = props.result?.workflow.run_id
  // 暂停是并行控制信号，即使轮询还在进行也允许点击；其他控制仍等待当前请求结束。
  if (!runId || (props.busy && action !== 'pause')) return
  emit('control', runId, {
    action,
    step_limit: stepLimit,
    ...(action === 'correct'
      ? { correction: { skip_tools: skipTools.value, note: correctionNote.value.trim() || undefined } }
      : {}),
  })
}

function sendFeedback(action: AgentFeedbackAction): void {
  const runId = props.result?.workflow.run_id
  if (!runId || props.busy || feedbackSent.value) return
  emit('feedback', runId, action)
  feedbackSent.value = true
}
</script>

<template>
  <section class="panel agent-panel">
    <div class="panel-heading"><span>销售 Agent</span><small>受控 v3 · 五工具</small></div>
    <p class="agent-help">综合分析会按步骤读取五类只读资料，再生成待人工编辑的草稿；不能直接发送消息或修改业务数据。</p>
    <p class="agent-cost">回复、标签、日程是单目标流程；综合分析会展示每一步的资料状态和缺失信息。</p>
    <label>任务类型
      <select v-model="task">
        <option value="auto">自动判断</option>
        <option value="reply">回复建议</option>
        <option value="tag">标签建议</option>
        <option value="schedule">日程建议</option>
        <option value="comprehensive">综合五工具分析</option>
      </select>
    </label>
    <label>给 Agent 的指令（可选）
      <input v-model="instruction" maxlength="500" placeholder="例如：帮我生成标签建议" />
    </label>
    <label v-if="task === 'comprehensive'">执行方式
      <select v-model="executionMode">
        <option value="complete">一次执行完成</option>
        <option value="checkpointed">分步暂停，人工检查后继续</option>
      </select>
    </label>
    <button type="button" class="primary" :disabled="customerId === null || busy" @click="submit">
      {{ busy ? 'Agent 执行中…' : '运行销售 Agent' }}
    </button>
    <p v-if="error" class="error">{{ error }}</p>
    <div v-if="result" class="agent-result">
      <strong>本次目标：{{ result.intent }}</strong>
      <span>受控工具：{{ result.selected_tool }} · {{ result.planned_by === 'explicit_task' ? '人工显式选择' : `规划器：${result.planned_by}` }}</span>
      <span>下一步：{{ result.workflow.next_action || result.workflow.status }}</span>
      <span v-if="result.workflow.status === 'queued' || result.workflow.status === 'running'" class="running-state">Worker 正在处理检查点…</span>
      <span v-if="result.human_confirmation_required" class="human-gate">需要人工确认</span>
      <div v-if="result.workflow.status === 'failed'" class="retry-box">
        <span>本次运行失败；最多允许 {{ result.workflow.max_attempts }} 次执行，当前已尝试 {{ result.workflow.attempt_count }} 次。</span>
        <button type="button" class="secondary" :disabled="busy || !result.workflow.retryable || !result.workflow.run_id" @click="emit('retry', result.workflow.run_id!)">
          {{ result.workflow.retryable ? '确认重试' : '已达到重试上限' }}
        </button>
      </div>
      <div v-if="result.steps.length" class="agent-steps">
        <strong>逐步查询结果</strong>
        <ol>
          <li v-for="step in result.steps" :key="`${step.step}-${step.tool_name}`" :class="step.status">
            <span>{{ step.tool_name }}</span><small>{{ step.summary }}</small>
          </li>
        </ol>
      </div>
      <div v-if="result.intent === 'comprehensive' && result.workflow.status === 'paused'" class="agent-controls">
        <strong>人工检查点</strong>
        <p>可以跳过不需要的资料域，再继续执行。跳过只影响本次分析，不会删除任何数据。</p>
        <div class="skip-grid">
          <label v-for="option in toolOptions" :key="option.value" class="skip-option">
            <input v-model="skipTools" type="checkbox" :value="option.value" />
            {{ option.label }}
          </label>
        </div>
        <input v-model="correctionNote" maxlength="300" placeholder="修正备注（可选）" />
        <div class="control-actions">
          <button type="button" class="secondary" :disabled="busy" @click="control('correct')">保存人工修正</button>
          <button type="button" class="primary" :disabled="busy" @click="control('resume', 1)">继续一步</button>
          <button type="button" class="primary" :disabled="busy" @click="control('resume', 5)">完成剩余步骤</button>
        </div>
      </div>
      <div v-if="result.intent === 'comprehensive' && (result.workflow.status === 'waiting_human' || result.workflow.status === 'failed')" class="feedback-box">
        <strong>人工反馈（帮助改进推理）</strong>
        <div class="control-actions">
          <button type="button" class="secondary" :disabled="busy || feedbackSent" @click="sendFeedback('incorrect_reasoning')">推理有问题</button>
          <button type="button" class="secondary" :disabled="busy || feedbackSent" @click="sendFeedback('missing_information')">信息不全</button>
          <button type="button" class="secondary" :disabled="busy || feedbackSent" @click="sendFeedback('not_useful')">这次不实用</button>
        </div>
        <small v-if="feedbackSent" class="feedback-success">反馈已记录</small>
      </div>
      <button v-if="result.workflow.status === 'queued' || result.workflow.status === 'running'" type="button" class="secondary" :disabled="!result.workflow.run_id" @click="control('pause')">请求暂停</button>
      <details>
        <summary>查看工具轨迹</summary>
        <ul><li v-for="item in result.tool_trace" :key="item.name"><strong>{{ item.name }}</strong> · {{ item.detail }}</li></ul>
      </details>
    </div>
  </section>
</template>

<style scoped>
.panel { display: grid; gap: 9px; padding: 16px; border: 1px solid #dbe3f0; border-radius: 14px; background: rgb(255 255 255 / 94%); box-shadow: 0 8px 22px rgb(30 64 175 / 5%); }
.panel-heading { display: flex; justify-content: space-between; color: #1e3a8a; font-weight: 700; }.panel-heading small { color: #64748b; font-weight: 400; }.agent-help { margin: 0; color: #64748b; font-size: 12px; line-height: 1.5; }
.agent-cost { margin: -4px 0 0; color: #92400e; font-size: 12px; line-height: 1.45; }
label { display: grid; gap: 4px; color: #475569; font-size: 12px; } select, input { box-sizing: border-box; width: 100%; padding: 8px; border: 1px solid #cbd5e1; border-radius: 7px; font: inherit; }
.primary { padding: 9px 11px; border: 0; border-radius: 8px; color: white; background: #2563eb; cursor: pointer; }.primary:disabled { opacity: .55; cursor: not-allowed; }.error { margin: 0; color: #b91c1c; }
.agent-result { display: grid; gap: 5px; padding: 10px; border-radius: 9px; color: #334155; background: #f8fafc; font-size: 12px; }.human-gate { color: #92400e; font-weight: 700; }.agent-result details { margin-top: 3px; }.agent-result ul { display: grid; gap: 5px; padding-left: 18px; color: #64748b; line-height: 1.4; }
.retry-box { display: grid; gap: 7px; padding: 9px; border: 1px solid #fecaca; border-radius: 8px; color: #991b1b; background: #fff1f2; }
.running-state { color: #1d4ed8; font-weight: 700; }
.agent-steps { display: grid; gap: 5px; margin-top: 4px; }.agent-steps ol { display: grid; gap: 6px; margin: 0; padding-left: 20px; }.agent-steps li { display: grid; gap: 2px; }.agent-steps li span { color: #334155; font-weight: 700; }.agent-steps li small { color: #64748b; line-height: 1.35; }.agent-steps li.incomplete { color: #b45309; }.agent-steps li.error { color: #b91c1c; }
.agent-controls { display: grid; gap: 7px; margin-top: 4px; padding-top: 8px; border-top: 1px solid #e2e8f0; }.agent-controls p { margin: 0; color: #64748b; line-height: 1.4; }.skip-grid { display: grid; gap: 4px; grid-template-columns: repeat(2, minmax(0, 1fr)); }.skip-option { display: flex; align-items: center; gap: 5px; color: #475569; }.skip-option input { width: auto; }.control-actions { display: flex; flex-wrap: wrap; gap: 6px; }.secondary { padding: 8px 10px; border: 1px solid #cbd5e1; border-radius: 8px; color: #334155; background: #fff; cursor: pointer; }.secondary:disabled { opacity: .55; cursor: not-allowed; }
.feedback-box { display: grid; gap: 7px; padding: 9px; border: 1px solid #bfdbfe; border-radius: 8px; background: #eff6ff; }.feedback-success { color: #15803d; }
</style>
