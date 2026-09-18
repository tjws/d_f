<script setup lang="ts">
import { onMounted, ref } from 'vue'
import {
  downloadAdminDataExport,
  getDataRetentionPolicy,
  getDetailedRetentionPolicy,
  previewRetention,
  purgeRetention,
  type DataRetentionPolicy,
  type ExportDataset,
  type ExportFormat,
} from '../../api/adminDataExport'

const dataset = ref<ExportDataset>('customers')
const format = ref<ExportFormat>('csv')
const start = ref('')
const end = ref('')
const limit = ref(1000)
const policy = ref<DataRetentionPolicy | null>(null)
const loadingPolicy = ref(true)
const exporting = ref(false)
const error = ref('')
const success = ref('')
const detailedPolicy = ref<Awaited<ReturnType<typeof getDetailedRetentionPolicy>> | null>(null)
const retentionDataset = ref('chat_messages')
const previewResult = ref<Awaited<ReturnType<typeof previewRetention>> | null>(null)
const purging = ref(false)

const datasetLabels: Record<ExportDataset, string> = {
  customers: '客户基础信息',
  chat_messages: '聊天消息索引',
  audit_logs: '审计日志',
  ai_feedback: 'AI 采用反馈',
}

async function loadPolicy(): Promise<void> {
  loadingPolicy.value = true
  try {
    policy.value = await getDataRetentionPolicy()
    detailedPolicy.value = await getDetailedRetentionPolicy()
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '保留策略加载失败'
  } finally {
    loadingPolicy.value = false
  }
}

async function previewData(): Promise<void> {
  error.value = ''
  try {
    previewResult.value = await previewRetention(retentionDataset.value)
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '预览失败'
  }
}

async function purgeData(): Promise<void> {
  if (!window.confirm('只清理已过期的聊天/反馈数据，且必须已开启环境开关。确定继续吗？')) return
  purging.value = true
  error.value = ''
  try {
    const result = await purgeRetention(retentionDataset.value, true)
    success.value = `已清理 ${result.deleted_rows} 条记录，审计日志 ID：${result.audit_log_id ?? '未知'}`
    previewResult.value = null
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '清理失败'
  } finally {
    purging.value = false
  }
}

async function exportData(): Promise<void> {
  error.value = ''
  success.value = ''
  if (start.value && end.value && start.value > end.value) {
    error.value = '开始日期不能晚于结束日期'
    return
  }
  exporting.value = true
  try {
    const result = await downloadAdminDataExport({ dataset: dataset.value, format: format.value, start: start.value || undefined, end: end.value || undefined, limit: limit.value })
    const url = URL.createObjectURL(result.blob)
    const link = document.createElement('a')
    link.href = url
    link.download = result.filename
    link.click()
    URL.revokeObjectURL(url)
    success.value = `已生成 ${datasetLabels[dataset.value]} 导出文件，并写入审计日志。`
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '导出失败'
  } finally {
    exporting.value = false
  }
}

onMounted(loadPolicy)
</script>

<template>
  <div class="admin-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">Data Governance</p>
        <h1>数据导出与保留</h1>
        <p>仅管理员可导出；默认脱敏，导出行为会记录到审计日志。</p>
      </div>
    </header>

    <section class="panel policy">
      <h2>当前策略</h2>
      <p v-if="loadingPolicy" class="muted">读取策略中…</p>
      <template v-else-if="policy">
        <div class="badges"><span>自动删除：{{ policy.automatic_deletion_enabled ? '开启' : '关闭' }}</span><span>默认脱敏：{{ policy.default_export_redacted ? '是' : '否' }}</span><span>删除前复核：{{ policy.review_before_delete ? '需要' : '不需要' }}</span></div>
        <p class="muted">{{ policy.note }}</p>
      </template>
      <p v-else class="muted">暂时无法读取策略。</p>
      <div v-if="detailedPolicy" class="retention-table">
        <div v-for="item in detailedPolicy.datasets" :key="item.dataset" class="retention-row"><strong>{{ datasetLabels[item.dataset as ExportDataset] || item.dataset }}</strong><span>{{ item.retention_days }} 天</span><span>{{ item.automatic_deletion_allowed ? '可受控清理' : '只读保留' }}</span></div>
      </div>
      <div v-if="detailedPolicy" class="retention-actions">
        <select v-model="retentionDataset"><option value="chat_messages">聊天消息</option><option value="ai_feedback">AI 反馈</option></select>
        <button type="button" @click="previewData">预览到期记录</button>
        <button type="button" class="danger" :disabled="purging || !detailedPolicy.automatic_deletion_enabled" @click="purgeData">{{ purging ? '清理中…' : '确认清理' }}</button>
      </div>
      <p v-if="previewResult" class="muted">预览：{{ previewResult.before }} 前有 {{ previewResult.matching_rows }} 条记录；{{ previewResult.deletion_allowed ? '当前允许受控清理' : '当前仅允许预览' }}。</p>
    </section>

    <section class="panel form-panel">
      <h2>生成导出文件</h2>
      <div class="form-grid">
        <label>数据集<select v-model="dataset"><option v-for="(label, key) in datasetLabels" :key="key" :value="key">{{ label }}</option></select></label>
        <label>格式<select v-model="format"><option value="csv">CSV（适合表格）</option><option value="json">JSON（适合程序）</option></select></label>
        <label>开始日期<input v-model="start" type="date"></label>
        <label>结束日期<input v-model="end" type="date"></label>
        <label>最多记录数<input v-model.number="limit" type="number" min="1" max="10000"></label>
      </div>
      <button type="button" :disabled="exporting" @click="exportData">{{ exporting ? '生成中…' : '生成并下载' }}</button>
      <p v-if="success" class="success">{{ success }}</p>
      <p v-if="error" class="error">{{ error }}</p>
    </section>

    <section class="panel note">
      <h2>导出边界</h2>
      <ul><li>客户姓名、手机号和 IP 地址会脱敏。</li><li>聊天只导出消息索引和截断后的脱敏预览，不导出 AES-GCM 密文。</li><li>AI 编辑内容正文不会导出，只保留是否存在的标记。</li><li>当前不提供自动删除，具体保留天数需客户确认后再配置。</li></ul>
    </section>
  </div>
</template>

<style scoped>
.admin-page { display: grid; gap: 18px; }
.page-header h1 { margin: 0; }
.page-header p:last-child, .muted { color: #64748b; }
.eyebrow { margin: 0 0 6px; color: #be123c; font-size: 12px; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; }
.panel { padding: 20px; border: 1px solid #dbe5ee; border-radius: 16px; background: white; box-shadow: 0 8px 22px rgb(190 18 60 / 5%); }
h2 { margin-top: 0; font-size: 18px; }
.badges { display: flex; flex-wrap: wrap; gap: 8px; }
.badges span { padding: 7px 10px; border-radius: 999px; color: #9f1239; background: #ffe4e6; font-size: 13px; }
.form-grid { display: grid; grid-template-columns: repeat(5, minmax(130px, 1fr)); gap: 12px; margin-bottom: 18px; }
label { display: grid; gap: 5px; color: #475569; font-size: 13px; }
select, input { min-width: 0; padding: 9px; border: 1px solid #cbd5e1; border-radius: 8px; background: white; }
button { padding: 10px 16px; border: 0; border-radius: 8px; color: white; background: #be123c; cursor: pointer; }
button:disabled { cursor: wait; opacity: .6; }
.success { color: #047857; }.error { color: #b91c1c; }
.retention-table { margin-top: 14px; border-top: 1px solid #e2e8f0; }.retention-row { display: grid; grid-template-columns: 1.5fr 1fr 1fr; gap: 8px; padding: 9px 0; border-bottom: 1px solid #e2e8f0; color: #475569; font-size: 13px; }.retention-actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px; }.retention-actions select { padding: 9px; border: 1px solid #cbd5e1; border-radius: 8px; }.danger { background: #991b1b; }.danger:disabled { opacity: .5; }
.note li { margin: 8px 0; color: #475569; }
@media (max-width: 760px) { .form-grid { grid-template-columns: 1fr; } }
</style>
