<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import CustomerProfilePanel from '../components/customer/CustomerProfilePanel.vue'
import AISuggestionPanel from '../components/customer/AISuggestionPanel.vue'
import TagPanel from '../components/customer/TagPanel.vue'
import SchedulePanel from '../components/customer/SchedulePanel.vue'
import CommunicationPanel from '../components/customer/CommunicationPanel.vue'
import { useCustomerWorkspace } from '../composables/useCustomerWorkspace'
import type { Customer } from '../types/customer'

const route = useRoute()
const customerId = computed(() => Number(route.params.customerId))

const {
  customer,
  latestProfile,
  replySuggestions,
  scheduleSuggestions,
  tags,
  schedules,
  chatMessages,
  timelineEvents,
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
} = useCustomerWorkspace(customerId)

const stageLabels: Record<Customer['stage'], string> = {
  new: '新客户',
  following_up: '跟进中',
  converted: '已转化',
  lost: '已流失',
}

function formatDate(value: string | null): string {
  if (!value) return '未设置'
  return new Date(value).toLocaleString('zh-CN')
}

onMounted(loadAll)
watch(customerId, loadAll)
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
            <button type="button" class="workflow-button" @click="runWorkflow">
              运行 AI 工作流
            </button>
          </div>
        </header>

        <p v-if="errors.workflow" class="workflow-error">
          {{ errors.workflow }}
        </p>

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

        <div class="workspace-grid">
          <CustomerProfilePanel
            :profile="latestProfile"
            :error="errors.profiles"
            @generate="generateProfileDraft"
            @edit="editProfile"
            @confirm="confirmProfile"
            @reject="rejectProfile"
          />

          <AISuggestionPanel
            :suggestions="replySuggestions"
            :error="errors.suggestions"
            @generate="generateReplyDraft"
            @edit="editSuggestion"
            @accept="acceptSuggestion"
            @reject="rejectSuggestion"
          />

          <TagPanel
            :tags="tags"
            :error="errors.tags"
            @generate="generateTagSuggestions"
            @confirm="confirmTag"
            @reject="rejectTag"
          />

          <SchedulePanel
            :suggestions="scheduleSuggestions"
            :schedules="schedules"
            :error="errors.schedules || errors.scheduleSuggestions"
            @generate="generateScheduleSuggestion"
            @edit="editScheduleSuggestion"
            @confirm="confirmSchedule"
            @complete="completeSchedule"
            @cancel="cancelScheduleItem"
          />
        </div>

        <CommunicationPanel
          :messages="chatMessages"
          :timeline-events="timelineEvents"
          :chat-error="errors.chat"
          :timeline-error="errors.timeline"
          @send-message="sendMockMessage"
        />
      </template>
    </div>
  </main>
</template>

<style scoped>
.workspace-page {
  min-height: 100vh;
  padding: 40px 6vw 64px;
  color: #1f2937;
  background: #f8fafc;
}

.workspace-container {
  max-width: 1180px;
  margin: 0 auto;
}

.back-link {
  display: inline-block;
  margin-bottom: 24px;
  color: #2563eb;
  text-decoration: none;
}

.customer-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  padding: 28px;
  border-radius: 20px;
  color: white;
  background: linear-gradient(135deg, #1d4ed8, #4338ca);
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
  font-size: 40px;
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
  padding: 16px;
  border-radius: 12px;
  background: white;
  box-shadow: 0 4px 14px rgb(15 23 42 / 5%);
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

.workspace-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.workspace-grid > * {
  min-width: 0;
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

@media (max-width: 900px) {
  .customer-summary,
  .workspace-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 560px) {
  .customer-summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .customer-header {
    flex-direction: column;
  }

  .header-actions {
    align-items: flex-start;
  }
}
</style>
