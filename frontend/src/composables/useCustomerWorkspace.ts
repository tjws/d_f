import { computed, reactive, ref, type Ref } from 'vue'
import { getCustomer } from '../api/customers'
import { archiveStudent, createStudent as createStudentRequest, listStudents, restoreStudent, updateStudent as updateStudentRequest } from '../api/students'
import {
  confirmCustomerProfile,
  listCustomerProfiles,
  rejectCustomerProfile,
  updateCustomerProfile,
} from '../api/customerProfiles'
import {
  acceptAISuggestion,
  listAISuggestions,
  rejectAISuggestion,
  updateAISuggestion,
} from '../api/aiSuggestions'
import { getAIWorkflowRun, runAIWorkflow, streamAIWorkflowRun } from '../api/aiWorkflow'
import {
  confirmCustomerTag,
  listCustomerTags,
  rejectCustomerTag,
} from '../api/tags'
import {
  cancelSchedule,
  completeSchedule as completeScheduleRequest,
  confirmScheduleSuggestion,
  listScheduleSuggestions,
  listSchedules,
  updateSchedule,
  updateScheduleSuggestion,
} from '../api/schedules'
import {
  createMockChatMessage,
  listChatMessages,
  transcribeChatMessage,
} from '../api/chatMessages'
import { sortChatMessagesForDisplay } from '../utils/chatMessages'
import {
  createTimelineEvent,
  listTimelineEvents,
} from '../api/timelineEvents'
import type { Customer } from '../types/customer'
import type { Student, StudentCreate, StudentUpdate } from '../types/student'
import type {
  CustomerProfile,
  CustomerProfileUpdate,
} from '../types/customerProfile'
import type {
  AISuggestion,
  AISuggestionUpdate,
} from '../types/aiSuggestion'
import type { CustomerTag } from '../types/tag'
import type { Schedule, ScheduleCompletion, ScheduleUpdate } from '../types/schedule'
import type {
  ChatMessage,
  ChatMessageCreate,
} from '../types/chatMessage'
import type {
  TimelineEvent,
  TimelineEventCreate,
} from '../types/timelineEvent'
import type { AIWorkflowGoal } from '../types/aiWorkflow'
import { createCourseOrder, listCourseOrders, updateCourseOrder } from '../api/courseOrders'
import { createServiceTicket as createServiceTicketRequest, listServiceTickets, updateServiceTicket } from '../api/serviceTickets'
import type { CourseOrder, CourseOrderCreate, CourseOrderStatus } from '../types/courseOrder'
import type { ServiceTicket, ServiceTicketCreate, ServiceTicketStatus } from '../types/serviceTicket'

export function useCustomerWorkspace(customerId: Ref<number>) {
  const customer = ref<Customer | null>(null)
  const profiles = ref<CustomerProfile[]>([])
  const suggestions = ref<AISuggestion[]>([])
  const scheduleSuggestions = ref<AISuggestion[]>([])
  const tags = ref<CustomerTag[]>([])
  const schedules = ref<Schedule[]>([])
  const chatMessages = ref<ChatMessage[]>([])
  const timelineEvents = ref<TimelineEvent[]>([])
  const students = ref<Student[]>([])
  const archivedStudents = ref<Student[]>([])
  const orders = ref<CourseOrder[]>([])
  const serviceTickets = ref<ServiceTicket[]>([])
  const workflowNotice = ref('')
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
      chatMessages.value = sortChatMessagesForDisplay(await listChatMessages(currentId()))
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

  async function loadStudents(): Promise<void> {
    try {
      clearError('students')
      const allStudents = await listStudents(currentId(), true)
      students.value = allStudents.filter((student) => !student.archived_at)
      archivedStudents.value = allStudents.filter((student) => Boolean(student.archived_at))
    } catch (error) {
      setError('students', error)
    }
  }

  async function loadOrders(): Promise<void> {
    try { clearError('orders'); orders.value = await listCourseOrders(currentId()) } catch (error) { setError('orders', error) }
  }

  async function loadServiceTickets(): Promise<void> {
    try { clearError('serviceTickets'); serviceTickets.value = await listServiceTickets(currentId()) } catch (error) { setError('serviceTickets', error) }
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
      loadStudents(),
      loadOrders(),
      loadServiceTickets(),
    ])

    loading.value = false
  }

  async function createStudent(payload: StudentCreate): Promise<void> {
    try {
      clearError('students')
      await createStudentRequest(currentId(), payload)
      await loadStudents()
      workflowNotice.value = '学生资料已保存，可作为 AI 分析上下文。'
    } catch (error) {
      setError('students', error)
    }
  }

  async function editStudent(studentId: number, payload: StudentUpdate): Promise<void> {
    try {
      clearError('students')
      await updateStudentRequest(currentId(), studentId, payload)
      await loadStudents()
      workflowNotice.value = '学生资料已更新。'
    } catch (error) {
      setError('students', error)
    }
  }

  async function archiveStudentRecord(studentId: number): Promise<void> {
    try {
      clearError('students')
      await archiveStudent(currentId(), studentId)
      await loadStudents()
      workflowNotice.value = '学生资料已归档，后续 AI 分析将不再使用。'
    } catch (error) {
      setError('students', error)
    }
  }

  async function restoreStudentRecord(studentId: number): Promise<void> {
    try {
      clearError('students')
      await restoreStudent(currentId(), studentId)
      await loadStudents()
      workflowNotice.value = '学生资料已恢复。'
    } catch (error) {
      setError('students', error)
    }
  }

  async function createOrder(payload: CourseOrderCreate): Promise<void> {
    try { clearError('orders'); await createCourseOrder(currentId(), payload); await Promise.all([loadOrders(), loadTimelineEvents()]) } catch (error) { setError('orders', error) }
  }

  async function updateOrder(orderId: number, status: CourseOrderStatus): Promise<void> {
    try { clearError('orders'); await updateCourseOrder(currentId(), orderId, { status }); await Promise.all([loadOrders(), loadCustomer(), loadTimelineEvents()]) } catch (error) { setError('orders', error) }
  }

  async function createTicketRecord(payload: ServiceTicketCreate): Promise<void> {
    try { clearError('serviceTickets'); await createServiceTicketRequest(currentId(), payload); await Promise.all([loadServiceTickets(), loadTimelineEvents()]) } catch (error) { setError('serviceTickets', error) }
  }

  async function updateServiceTicketStatus(ticketId: number, status: ServiceTicketStatus): Promise<void> {
    try { clearError('serviceTickets'); await updateServiceTicket(currentId(), ticketId, { status }); await Promise.all([loadServiceTickets(), loadTimelineEvents()]) } catch (error) { setError('serviceTickets', error) }
  }

  async function generateProfileDraft(): Promise<void> {
    await runWorkflow('profile')
  }

  async function editProfile(
    profileId: number,
    payload: CustomerProfileUpdate,
  ): Promise<void> {
    await updateCustomerProfile(currentId(), profileId, payload)
    await loadProfiles()
    workflowNotice.value = '客户画像已保存为人工编辑版本。请核对内容后再决定是否确认。'
  }

  async function confirmProfile(profileId: number): Promise<void> {
    await confirmCustomerProfile(currentId(), profileId)
    await loadProfiles()
    // 确认只更新客户档案；下一步是否调用模型仍由销售人员主动决定。
    workflowNotice.value = '客户画像已确认并更新客户档案。下一步可手动生成回复建议、查看沟通记录或安排跟进。'
  }

  async function rejectProfile(profileId: number): Promise<void> {
    await rejectCustomerProfile(currentId(), profileId)
    await loadProfiles()
    workflowNotice.value = '客户画像草稿已拒绝，客户正式档案未发生变化。'
  }

  async function generateReplyDraft(): Promise<void> {
    await runWorkflow('reply')
  }

  async function runWorkflow(goal: AIWorkflowGoal = 'reply'): Promise<void> {
    try {
      clearError('workflow')
      workflowNotice.value = ''
      let result = await runAIWorkflow(currentId(), goal)
      if (
        result.run_id !== null
        && (result.status === 'queued' || result.status === 'running')
      ) {
        workflowNotice.value = 'AI 任务已进入队列，正在生成草稿…'
        result = await waitForWorkflowRun(result.run_id)
      }
      await Promise.all([
        loadProfiles(),
        loadSuggestions(),
        loadTags(),
        loadScheduleSuggestions(),
        loadTimelineEvents(),
      ])

      if (result.next_action === 'confirm_profile') {
        workflowNotice.value = '已生成画像草稿，请先在客户画像面板人工确认，再运行工作流生成回复建议。'
      } else if (result.next_action === 'review_reply') {
        workflowNotice.value = '已生成回复草稿，请在 AI 回复建议面板人工编辑、接受或拒绝。'
      } else if (result.next_action === 'confirm_tags') {
        workflowNotice.value = '已生成标签建议，请在客户标签面板人工确认或拒绝。'
      } else if (result.next_action === 'review_schedule') {
        workflowNotice.value = '已生成日程草稿，请在跟进日程面板人工编辑并确认。'
      }
    } catch (error) {
      setError('workflow', error)
    }
  }

  async function waitForWorkflowRun(runId: number): Promise<import('../types/aiWorkflow').AIWorkflowRun> {
    try {
      return await streamAIWorkflowRun(currentId(), runId, (update) => {
        workflowNotice.value = update.status === 'running'
          ? 'AI 正在生成草稿…'
          : 'AI 任务已进入队列，正在等待 Worker…'
      })
    } catch {
      // SSE 可能被旧代理或网络中断；保留轮询回退，避免影响现有工作台。
      workflowNotice.value = '实时推送暂不可用，正在使用状态查询…'
      for (let attempt = 0; attempt < 15; attempt += 1) {
        await new Promise((resolve) => window.setTimeout(resolve, 2000))
        const result = await getAIWorkflowRun(currentId(), runId)
        if (result.status !== 'queued' && result.status !== 'running') {
          return result
        }
      }
    }
    throw new Error('AI 任务仍在处理中，请稍后刷新页面查看结果')
  }

  async function editSuggestion(
    suggestionId: number,
    payload: AISuggestionUpdate,
  ): Promise<void> {
    await updateAISuggestion(currentId(), suggestionId, payload)
    await loadSuggestions()
    workflowNotice.value = '回复建议已保存为人工编辑版本。请核对内容后，接受建议或继续修改。'
  }

  async function acceptSuggestion(suggestionId: number): Promise<void> {
    await acceptAISuggestion(currentId(), suggestionId)
    await Promise.all([loadSuggestions(), loadTimelineEvents()])
    workflowNotice.value = '回复建议已接受，尚未发送给家长。下一步请放入聊天输入框，检查后再由你确认发送。'
  }

  async function rejectSuggestion(suggestionId: number): Promise<void> {
    await rejectAISuggestion(currentId(), suggestionId)
    await Promise.all([loadSuggestions(), loadTimelineEvents()])
    workflowNotice.value = '回复建议已拒绝，没有向家长发送任何内容。你可以重新生成建议，或直接人工回复。'
  }

  async function generateTagSuggestions(): Promise<void> {
    await runWorkflow('tag')
  }

  async function confirmTag(customerTagId: number): Promise<void> {
    await confirmCustomerTag(currentId(), customerTagId)
    await Promise.all([loadTags(), loadTimelineEvents()])
    workflowNotice.value = '客户标签已确认并同步到客户档案。下一步可继续处理回复建议或安排跟进。'
  }

  async function rejectTag(customerTagId: number): Promise<void> {
    await rejectCustomerTag(currentId(), customerTagId)
    await Promise.all([loadTags(), loadTimelineEvents()])
    workflowNotice.value = '标签建议已拒绝，客户正式标签没有变化。'
  }

  async function generateScheduleSuggestion(): Promise<void> {
    await runWorkflow('schedule')
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
    workflowNotice.value = '跟进日程已确认并写入日程表。请在约定时间完成跟进，再记录结果。'
  }

  async function editSchedule(
    scheduleId: number,
    payload: ScheduleUpdate,
  ): Promise<void> {
    await updateSchedule(currentId(), scheduleId, payload)
    await loadSchedules()
  }

  async function completeSchedule(scheduleId: number, payload: ScheduleCompletion = { outcome: 'other' }): Promise<void> {
    await completeScheduleRequest(currentId(), scheduleId, payload)
    await Promise.all([loadSchedules(), loadTimelineEvents()])
  }

  async function cancelScheduleItem(scheduleId: number): Promise<void> {
    await cancelSchedule(currentId(), scheduleId)
    await Promise.all([loadSchedules(), loadTimelineEvents()])
  }

  async function sendMockMessage(payload: ChatMessageCreate): Promise<void> {
    try {
      clearError('chat')
      await createMockChatMessage(currentId(), payload)
      // 聊天写入会由后端事务同步生成时间线事件，因此两边一起刷新。
      await Promise.all([loadChatMessages(), loadTimelineEvents()])
      workflowNotice.value = payload.direction === 'outbound'
        ? '消息已由你确认发送，聊天记录和客户时间线已同步更新。下一步可等待家长回复或安排后续跟进。'
        : '家长消息已记录，客户时间线已同步更新。你可以生成回复建议，或直接人工回复。'
    } catch (error) {
      setError('chat', error)
    }
  }

  async function transcribeMessage(messageId: number): Promise<void> {
    try {
      clearError('chat')
      await transcribeChatMessage(currentId(), messageId)
      await Promise.all([loadChatMessages(), loadTimelineEvents()])
    } catch (error) {
      setError('chat', error)
    }
  }

  async function addTimelineEvent(payload: TimelineEventCreate): Promise<void> {
    try {
      clearError('timeline')
      await createTimelineEvent(currentId(), payload)
      await loadTimelineEvents()
    } catch (error) {
      setError('timeline', error)
    }
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
    students,
    archivedStudents,
    orders,
    serviceTickets,
    workflowNotice,
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
    loadStudents,
    loadOrders,
    loadServiceTickets,
    createStudent,
    editStudent,
    archiveStudentRecord,
    restoreStudentRecord,
    createOrder,
    updateOrder,
    createServiceTicket: createTicketRecord,
    updateServiceTicketStatus,
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
    transcribeMessage,
    addTimelineEvent,
  }
}
