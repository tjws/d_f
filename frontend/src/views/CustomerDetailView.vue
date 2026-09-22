<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import CustomerProfilePanel from '../components/customer/CustomerProfilePanel.vue'
import AISuggestionPanel from '../components/customer/AISuggestionPanel.vue'
import TagPanel from '../components/customer/TagPanel.vue'
import SchedulePanel from '../components/customer/SchedulePanel.vue'
import CommunicationPanel from '../components/customer/CommunicationPanel.vue'
import SalesMaterialPanel from '../components/customer/SalesMaterialPanel.vue'
import StudentPanel from '../components/customer/StudentPanel.vue'
import CustomerTransferPanel from '../components/customer/CustomerTransferPanel.vue'
import { useCustomerWorkspace } from '../composables/useCustomerWorkspace'
import type { Customer } from '../types/customer'
import type { ChatMessageCreate } from '../types/chatMessage'

const route = useRoute()
const customerId = computed(() => Number(route.params.customerId))
type WorkspaceTab = 'overview' | 'communication' | 'ai' | 'followup'
const activeTab = ref<WorkspaceTab>('overview')
const workspaceTabs: Array<{ value: WorkspaceTab; label: string; hint: string }> = [
  { value: 'overview', label: '概览', hint: '客户与学生资料' },
  { value: 'communication', label: '沟通', hint: '聊天与时间线' },
  { value: 'ai', label: 'AI 助手', hint: '草稿需人工处理' },
  { value: 'followup', label: '跟进', hint: '日程与转移' },
]
const reviewFocus = computed(() => {
  const value = route.query.focus
  return value === 'profile' || value === 'reply' || value === 'tag' || value === 'schedule' ? value : null
})

function tabFromQuery(value: unknown): WorkspaceTab | null {
  return typeof value === 'string' && workspaceTabs.some((tab) => tab.value === value)
    ? value as WorkspaceTab
    : null
}

const {
  customer,
  latestProfile,
  replySuggestions,
  scheduleSuggestions,
  tags,
  schedules,
  chatMessages,
  timelineEvents,
  students,
  archivedStudents,
  workflowNotice,
  loading,
  errors,
  loadAll,
  generateProfileDraft,
  editProfile,
  confirmProfile,
  rejectProfile,
  generateReplyDraft,
  runWorkflow,
  editSuggestion,
  acceptSuggestion,
  rejectSuggestion,
  generateTagSuggestions,
  confirmTag,
  rejectTag,
  generateScheduleSuggestion,
  editScheduleSuggestion,
  confirmSchedule,
  completeSchedule,
  cancelScheduleItem,
  sendMockMessage,
  transcribeMessage,
  addTimelineEvent,
  createStudent,
  editStudent,
  archiveStudentRecord,
  restoreStudentRecord,
} = useCustomerWorkspace(customerId)

const stageLabels: Record<Customer['stage'], string> = {
  new: '新客户',
  following_up: '跟进中',
  converted: '已转化',
  lost: '已流失',
}

const replyDraftForSend = ref<{ suggestionId: number; text: string } | null>(null)
const latestReplySuggestion = computed(() => replySuggestions.value[0] ?? null)
// 顶部动作必须由“刚完成的业务步骤”决定，不能被客户历史上的旧建议状态抢占。
const noticeIsProfileDraft = computed(() => workflowNotice.value.startsWith('已生成画像草稿'))
const noticeIsProfileConfirmed = computed(() => workflowNotice.value.startsWith('客户画像已确认'))
const noticeIsReplyDraft = computed(() => workflowNotice.value.startsWith('已生成回复草稿'))
const noticeIsReplyAccepted = computed(() => workflowNotice.value.startsWith('回复建议已接受'))

function formatDate(value: string | null): string {
  if (!value) return '未设置'
  return new Date(value).toLocaleString('zh-CN')
}

function generateReplyFromConfirmedProfile(): void {
  activeTab.value = 'ai'
  void runWorkflow('reply')
}

function generateReplyFromSalesMaterials(): void {
  activeTab.value = 'ai'
  void runWorkflow('reply')
}

function prepareReplyForSending(suggestionId: number, text: string): void {
  replyDraftForSend.value = { suggestionId, text }
  activeTab.value = 'communication'
  workflowNotice.value = '回复建议已放入聊天输入框。请检查内容后，点击“确认 Mock 发送”。'
}

async function handleMockSend(payload: ChatMessageCreate): Promise<void> {
  await sendMockMessage(payload)
  // 发送成功后移除本次预填状态，避免旧草稿再次出现在聊天编辑区。
  if (!errors.chat) {
    replyDraftForSend.value = null
  }
}

function openReplySuggestion(): void {
  activeTab.value = 'ai'
}

function openProfileReview(): void {
  activeTab.value = 'overview'
}

onMounted(loadAll)
watch(customerId, loadAll)
watch(() => route.query.tab, (tab) => {
  const resolvedTab = tabFromQuery(tab)
  if (resolvedTab) activeTab.value = resolvedTab
}, { immediate: true })
</script>

<template>
  <main class="workspace-page">
    <div class="workspace-container">
      <RouterLink class="back-link" to="/customers">
        ← 返回客户列表
      </RouterLink>

      <p v-if="!customer && loading" class="state-message">
        正在加载客户工作台...
      </p>

      <p v-else-if="!customer && errors.customer" class="state-message error">
        {{ errors.customer }}
      </p>

      <template v-else-if="customer">
        <header class="customer-header">
          <div>
            <p class="eyebrow">Customer Workspace</p>
            <h1>{{ customer.name }}</h1>
            <p class="phone">{{ customer.phone }}</p>
          </div>
          <div class="header-actions">
            <span class="stage">{{ stageLabels[customer.stage] }}</span>
            <button type="button" class="workflow-button" @click="() => runWorkflow('reply')">
              运行 AI 工作流
            </button>
          </div>
        </header>

        <p v-if="errors.workflow" class="workflow-error">
          {{ errors.workflow }}
        </p>
        <div v-else-if="workflowNotice" class="workflow-notice">
          <span>{{ workflowNotice }}</span>
          <div class="notice-actions">
            <button v-if="noticeIsProfileDraft" type="button" @click="openProfileReview">审阅客户画像</button>
            <button v-else-if="noticeIsProfileConfirmed" type="button" @click="generateReplyFromConfirmedProfile">生成回复建议</button>
            <button v-else-if="noticeIsReplyDraft" type="button" @click="openReplySuggestion">审阅回复草稿</button>
            <button v-else-if="noticeIsReplyAccepted && latestReplySuggestion" type="button" @click="prepareReplyForSending(latestReplySuggestion.id, String(latestReplySuggestion.edited_content?.text ?? latestReplySuggestion.content.text ?? ''))">放入聊天输入框</button>
            <button type="button" class="ghost" @click="activeTab = 'communication'">查看沟通记录</button>
            <button type="button" class="ghost" @click="activeTab = 'followup'">安排跟进</button>
          </div>
        </div>

        <section class="customer-summary">
          <div>
            <span>学生</span>
            <strong>{{ customer.student_name || '未填写' }}</strong>
          </div>
          <div>
            <span>年级</span>
            <strong>{{ customer.grade || '未填写' }}</strong>
          </div>
          <div>
            <span>关注科目</span>
            <strong>{{ customer.interested_subject || '未填写' }}</strong>
          </div>
          <div>
            <span>下次跟进</span>
            <strong>{{ formatDate(customer.next_follow_up_at) }}</strong>
          </div>
        </section>

        <nav class="workspace-tabs" aria-label="客户工作台功能">
          <button v-for="tab in workspaceTabs" :key="tab.value" type="button" :class="{ active: activeTab === tab.value }" @click="activeTab = tab.value">
            <strong>{{ tab.label }}</strong><span>{{ tab.hint }}</span>
          </button>
        </nav>

        <div v-if="activeTab === 'overview'" class="workspace-grid">
          <StudentPanel :students="students" :archived-students="archivedStudents" :error="errors.students" :saving="loading" @create="createStudent" @update="editStudent" @archive="archiveStudentRecord" @restore="restoreStudentRecord" />
          <CustomerProfilePanel :profile="latestProfile" :error="errors.profiles" @generate="generateProfileDraft" @edit="editProfile" @confirm="confirmProfile" @reject="rejectProfile" />
        </div>

        <div v-else-if="activeTab === 'communication'" class="communication-workspace">
          <CommunicationPanel :messages="chatMessages" :timeline-events="timelineEvents" :chat-error="errors.chat" :timeline-error="errors.timeline" :prefill-text="replyDraftForSend?.text" :suggestion-id="replyDraftForSend?.suggestionId" @send-message="handleMockSend" @transcribe-message="transcribeMessage" @create-timeline-event="addTimelineEvent" />
          <SalesMaterialPanel :messages="chatMessages" :generating="loading" @generate="generateReplyFromSalesMaterials" />
        </div>

        <div v-else-if="activeTab === 'ai'" class="workspace-grid">
          <AISuggestionPanel v-if="!reviewFocus || reviewFocus === 'reply'" :suggestions="replySuggestions" :error="errors.suggestions" @generate="generateReplyDraft" @edit="editSuggestion" @accept="acceptSuggestion" @reject="rejectSuggestion" @use="prepareReplyForSending" />
          <TagPanel v-if="!reviewFocus || reviewFocus === 'tag'" :tags="tags" :error="errors.tags" @generate="generateTagSuggestions" @confirm="confirmTag" @reject="rejectTag" />
          <CustomerProfilePanel v-if="!reviewFocus || reviewFocus === 'profile'" :profile="latestProfile" :error="errors.profiles" @generate="generateProfileDraft" @edit="editProfile" @confirm="confirmProfile" @reject="rejectProfile" />
        </div>

        <div v-else-if="activeTab === 'followup'" class="workspace-grid">
          <SchedulePanel :suggestions="scheduleSuggestions" :schedules="schedules" :error="errors.schedules || errors.scheduleSuggestions" @generate="generateScheduleSuggestion" @edit="editScheduleSuggestion" @confirm="confirmSchedule" @complete="completeSchedule" @cancel="cancelScheduleItem" />
          <CustomerTransferPanel v-if="reviewFocus !== 'schedule'" :customer="customer" @transferred="loadAll" />
        </div>

      </template>
    </div>
  </main>
</template>

<style scoped>
.workspace-page {
  min-height: 100vh;
  padding: 30px 5vw 72px;
  color: #1f2937;
  background: radial-gradient(circle at 88% -4%, rgb(79 70 229 / 12%), transparent 29rem), linear-gradient(180deg, #eef5ff 0, #f8fbff 360px);
}

.workspace-container {
  max-width: 1180px;
  margin: 0 auto;
}

.back-link {
  display: inline-block;
  margin-bottom: 18px;
  padding: 7px 10px;
  border-radius: 8px;
  color: #2563eb;
  background: rgb(255 255 255 / 72%);
  text-decoration: none;
  font-weight: 600;
}
.back-link:hover { background: #fff; }

.customer-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  padding: clamp(24px, 4vw, 36px);
  border: 1px solid rgb(255 255 255 / 22%);
  border-radius: 22px;
  color: white;
  background: linear-gradient(135deg, #1d4ed8, #4338ca 70%, #5b21b6);
  box-shadow: 0 20px 42px rgb(30 64 175 / 20%);
}

.eyebrow {
  margin: 0 0 8px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  opacity: 0.8;
}

h1 {
  margin: 0;
  font-size: clamp(34px, 5vw, 46px);
}

.phone {
  margin-bottom: 0;
  opacity: 0.85;
}

.header-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 12px;
}

.workflow-button {
  padding: 10px 14px;
  border: 1px solid rgb(255 255 255 / 45%);
  border-radius: 9px;
  color: white;
  background: rgb(15 23 42 / 22%);
  cursor: pointer;
}

.workflow-button:hover {
  background: rgb(15 23 42 / 35%);
}

.stage {
  padding: 7px 13px;
  border-radius: 999px;
  color: #1e3a8a;
  background: #dbeafe;
}

.customer-summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin: 16px 0;
}

.customer-summary div {
  padding: 17px;
  border-radius: 14px;
  background: linear-gradient(145deg, #fff, #fbfdff);
  border: 1px solid var(--line);
  box-shadow: var(--shadow-sm);
}

.customer-summary span,
.customer-summary strong {
  display: block;
}

.customer-summary span {
  margin-bottom: 6px;
  color: #64748b;
  font-size: 13px;
}

/* 将完整客户档案按销售动作分段，避免把所有模块一次堆在同一页。 */
.workspace-tabs { display: flex; gap: 8px; margin: 20px 0 16px; padding: 7px; overflow-x: auto; border: 1px solid var(--line); border-radius: 16px; background: rgb(255 255 255 / 72%); box-shadow: var(--shadow-sm); }
.workspace-tabs button { display: grid; flex: 1 0 135px; gap: 3px; padding: 11px 13px; border: 0; border-radius: 11px; color: #64748b; background: transparent; text-align: left; cursor: pointer; }
.workspace-tabs strong { color: #334155; font-size: 14px; }.workspace-tabs span { font-size: 11px; }.workspace-tabs button:hover { background: #f1f5f9; }.workspace-tabs button.active { color: #1d4ed8; background: #eaf1ff; }.workspace-tabs button.active strong { color: #1d4ed8; }

.workspace-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.communication-workspace { display: grid; grid-template-columns: minmax(0, 1fr) minmax(290px, 340px); gap: 18px; align-items: start; }

.workspace-grid > * {
  min-width: 0;
}

/* 子模块共享同一张“业务卡片”外观，内容和操作规则仍由各自组件管理。 */
.workspace-grid :deep(.panel),
.workspace-container :deep(.communication-panel) {
  border-color: var(--line);
  border-radius: var(--radius-md);
  background: linear-gradient(145deg, #fff, #fbfdff);
  box-shadow: var(--shadow-sm);
}

.workspace-grid :deep(.panel:hover),
.workspace-container :deep(.communication-panel:hover) {
  border-color: #c7daf8;
}

.state-message {
  margin: 40px 0;
  color: #64748b;
}

.error {
  color: #dc2626;
}

.workflow-error {
  margin: 12px 0;
  color: #dc2626;
}

.workflow-notice { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin: 12px 0; padding: 12px 14px; border: 1px solid #bbf7d0; border-radius: 11px; color: #166534; background: #f0fdf4; }.notice-actions { display: flex; flex-wrap: wrap; gap: 8px; }.notice-actions button { padding: 7px 10px; border: 0; border-radius: 8px; color: white; background: #15803d; cursor: pointer; }.notice-actions .ghost { color: #166534; background: #dcfce7; }

@media (max-width: 900px) {
  .customer-summary,
  .workspace-grid,
  .communication-workspace {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 560px) {
  .workspace-page { padding: 20px 18px 48px; }
  .customer-summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .customer-header {
    flex-direction: column;
  }

  .header-actions {
    align-items: flex-start;
  }

  .workflow-notice { align-items: flex-start; flex-direction: column; }
}
</style>
