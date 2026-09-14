import { computed, reactive, ref, type Ref } from 'vue'
import { getCustomer } from '../api/customers'
import {
  confirmCustomerProfile,
  createCustomerProfileDraft,
  listCustomerProfiles,
  rejectCustomerProfile,
  updateCustomerProfile,
} from '../api/customerProfiles'
import {
  acceptAISuggestion,
  createReplyDraft,
  listAISuggestions,
  rejectAISuggestion,
  updateAISuggestion,
} from '../api/aiSuggestions'
import { runAIWorkflow } from '../api/aiWorkflow'
import {
  confirmCustomerTag,
  listCustomerTags,
  rejectCustomerTag,
  suggestCustomerTags,
} from '../api/tags'
import {
  cancelSchedule,
  completeSchedule as completeScheduleRequest,
  confirmScheduleSuggestion,
  createScheduleSuggestion,
  listScheduleSuggestions,
  listSchedules,
  updateSchedule,
  updateScheduleSuggestion,
} from '../api/schedules'
import {
  createMockChatMessage,
  listChatMessages,
} from '../api/chatMessages'
import {
  createTimelineEvent,
  listTimelineEvents,
} from '../api/timelineEvents'
import type { Customer } from '../types/customer'
import type {
  CustomerProfile,
  CustomerProfileUpdate,
} from '../types/customerProfile'
import type {
  AISuggestion,
  AISuggestionUpdate,
} from '../types/aiSuggestion'
import type { CustomerTag } from '../types/tag'
import type { Schedule, ScheduleUpdate } from '../types/schedule'
import type {
  ChatMessage,
  ChatMessageCreate,
} from '../types/chatMessage'
import type {
  TimelineEvent,
  TimelineEventCreate,
} from '../types/timelineEvent'

export function useCustomerWorkspace(customerId: Ref<number>) {
  const customer = ref<Customer | null>(null)
  const profiles = ref<CustomerProfile[]>([])
  const suggestions = ref<AISuggestion[]>([])
  const scheduleSuggestions = ref<AISuggestion[]>([])
  const tags = ref<CustomerTag[]>([])
  const schedules = ref<Schedule[]>([])
  const chatMessages = ref<ChatMessage[]>([])
  const timelineEvents = ref<TimelineEvent[]>([])
  const loading = ref(false)
  const errors = reactive<Record<string, string>>({})

  const latestProfile = computed(
    () => profiles.value[0] ?? null,
  )

  const replySuggestions = computed(() =>
    suggestions.value.filter((item) => item.suggestion_type === 'reply'),
  )

  function currentId(): number {
    return customerId.value
  }

  function setError(key: string, error: unknown): void {
    errors[key] = error instanceof Error ? error.message : '请求失败'
  }

  function clearError(key: string): void {
    delete errors[key]
  }

  async function loadCustomer(): Promise<void> {
    try {
      clearError('customer')
      customer.value = await getCustomer(currentId())
    } catch (error) {
      setError('customer', error)
    }
  }

  async function loadProfiles(): Promise<void> {
    try {
      clearError('profiles')
      profiles.value = await listCustomerProfiles(currentId())
    } catch (error) {
      setError('profiles', error)
    }
  }

  async function loadSuggestions(): Promise<void> {
    try {
      clearError('suggestions')
      suggestions.value = await listAISuggestions(currentId())
    } catch (error) {
      setError('suggestions', error)
    }
  }

  async function loadScheduleSuggestions(): Promise<void> {
    try {
      clearError('scheduleSuggestions')
      scheduleSuggestions.value = await listScheduleSuggestions(currentId())
    } catch (error) {
      setError('scheduleSuggestions', error)
    }
  }

  async function loadTags(): Promise<void> {
    try {
      clearError('tags')
      tags.value = await listCustomerTags(currentId())
    } catch (error) {
      setError('tags', error)
    }
  }

  async function loadSchedules(): Promise<void> {
    try {
      clearError('schedules')
      schedules.value = await listSchedules(currentId())
    } catch (error) {
      setError('schedules', error)
    }
  }

  async function loadChatMessages(): Promise<void> {
    try {
      clearError('chat')
      chatMessages.value = await listChatMessages(currentId())
    } catch (error) {
      setError('chat', error)
    }
  }

  async function loadTimelineEvents(): Promise<void> {
    try {
      clearError('timeline')
      timelineEvents.value = await listTimelineEvents(currentId())
    } catch (error) {
      setError('timeline', error)
    }
  }

  async function loadAll(): Promise<void> {
    loading.value = true

    // 各面板独立处理失败，避免一个模块故障导致整个客户工作台白屏。
    await Promise.allSettled([
      loadCustomer(),
      loadProfiles(),
      loadSuggestions(),
      loadScheduleSuggestions(),
      loadTags(),
      loadSchedules(),
      loadChatMessages(),
      loadTimelineEvents(),
    ])

    loading.value = false
  }

  async function generateProfileDraft(): Promise<void> {
    await createCustomerProfileDraft(currentId())
    await loadProfiles()
  }

  async function editProfile(
    profileId: number,
    payload: CustomerProfileUpdate,
  ): Promise<void> {
    await updateCustomerProfile(currentId(), profileId, payload)
    await loadProfiles()
  }

  async function confirmProfile(profileId: number): Promise<void> {
    await confirmCustomerProfile(currentId(), profileId)
    await loadProfiles()
  }

  async function rejectProfile(profileId: number): Promise<void> {
    await rejectCustomerProfile(currentId(), profileId)
    await loadProfiles()
  }

  async function generateReplyDraft(): Promise<void> {
    await createReplyDraft(currentId())
    await Promise.all([loadSuggestions(), loadTimelineEvents()])
  }

  async function runWorkflow(): Promise<void> {
    try {
      clearError('workflow')
      await runAIWorkflow(currentId())
      // 工作流生成的是草稿；刷新后仍由现有建议面板负责人工编辑和确认。
      await Promise.all([loadSuggestions(), loadTimelineEvents()])
    } catch (error) {
      setError('workflow', error)
    }
  }

  async function editSuggestion(
    suggestionId: number,
    payload: AISuggestionUpdate,
  ): Promise<void> {
    await updateAISuggestion(currentId(), suggestionId, payload)
    await loadSuggestions()
  }

  async function acceptSuggestion(suggestionId: number): Promise<void> {
    await acceptAISuggestion(currentId(), suggestionId)
    await Promise.all([loadSuggestions(), loadTimelineEvents()])
  }

  async function rejectSuggestion(suggestionId: number): Promise<void> {
    await rejectAISuggestion(currentId(), suggestionId)
    await Promise.all([loadSuggestions(), loadTimelineEvents()])
  }

  async function generateTagSuggestions(): Promise<void> {
    await suggestCustomerTags(currentId())
    await Promise.all([loadTags(), loadTimelineEvents()])
  }

  async function confirmTag(customerTagId: number): Promise<void> {
    await confirmCustomerTag(currentId(), customerTagId)
    await Promise.all([loadTags(), loadTimelineEvents()])
  }

  async function rejectTag(customerTagId: number): Promise<void> {
    await rejectCustomerTag(currentId(), customerTagId)
    await Promise.all([loadTags(), loadTimelineEvents()])
  }

  async function generateScheduleSuggestion(): Promise<void> {
    await createScheduleSuggestion(currentId())
    await loadScheduleSuggestions()
  }

  async function editScheduleSuggestion(
    suggestionId: number,
    payload: AISuggestionUpdate,
  ): Promise<void> {
    await updateScheduleSuggestion(currentId(), suggestionId, payload)
    await loadScheduleSuggestions()
  }

  async function confirmSchedule(suggestionId: number): Promise<void> {
    await confirmScheduleSuggestion(currentId(), suggestionId)
    await Promise.all([loadScheduleSuggestions(), loadSchedules(), loadTimelineEvents()])
  }

  async function editSchedule(
    scheduleId: number,
    payload: ScheduleUpdate,
  ): Promise<void> {
    await updateSchedule(currentId(), scheduleId, payload)
    await loadSchedules()
  }

  async function completeSchedule(scheduleId: number): Promise<void> {
    await completeScheduleRequest(currentId(), scheduleId)
    await Promise.all([loadSchedules(), loadTimelineEvents()])
  }

  async function cancelScheduleItem(scheduleId: number): Promise<void> {
    await cancelSchedule(currentId(), scheduleId)
    await Promise.all([loadSchedules(), loadTimelineEvents()])
  }

  async function sendMockMessage(payload: ChatMessageCreate): Promise<void> {
    await createMockChatMessage(currentId(), payload)
    await Promise.all([loadChatMessages(), loadTimelineEvents()])
  }

  async function addTimelineEvent(payload: TimelineEventCreate): Promise<void> {
    await createTimelineEvent(currentId(), payload)
    await loadTimelineEvents()
  }

  return {
    customer,
    profiles,
    latestProfile,
    suggestions,
    replySuggestions,
    scheduleSuggestions,
    tags,
    schedules,
    chatMessages,
    timelineEvents,
    loading,
    errors,
    loadAll,
    loadCustomer,
    loadProfiles,
    loadSuggestions,
    loadScheduleSuggestions,
    loadTags,
    loadSchedules,
    loadChatMessages,
    loadTimelineEvents,
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
    editSchedule,
    completeSchedule,
    cancelScheduleItem,
    sendMockMessage,
    addTimelineEvent,
  }
}
