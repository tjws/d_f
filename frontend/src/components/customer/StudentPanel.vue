<script setup lang="ts">
import { reactive, ref } from 'vue'
import type { Student, StudentCreate, StudentUpdate } from '../../types/student'

const props = defineProps<{ students: Student[]; archivedStudents: Student[]; error?: string; saving?: boolean }>()
const emit = defineEmits<{ create: [payload: StudentCreate]; update: [id: number, payload: StudentUpdate]; archive: [id: number]; restore: [id: number] }>()
const open = ref(false)
const editingId = ref<number | null>(null)
const form = reactive<StudentCreate>({ name: '', gender: '', grade: '', school: '' })

function startEdit(student: Student): void {
  editingId.value = student.id
  form.name = student.name
  form.gender = student.gender ?? ''
  form.grade = student.grade ?? ''
  form.school = student.school ?? ''
  open.value = true
}

function save(): void {
  const name = form.name.trim()
  if (!name) return
  const payload = { name, gender: form.gender?.trim() || null, grade: form.grade?.trim() || null, school: form.school?.trim() || null }
  if (editingId.value === null) emit('create', payload)
  else emit('update', editingId.value, payload)
  editingId.value = null
  form.name = ''; form.gender = ''; form.grade = ''; form.school = ''; open.value = false
}
</script>

<template>
  <section class="panel">
    <div class="panel-heading">
      <div><p class="eyebrow">Student Profile</p><h2>学生资料</h2></div>
      <button type="button" @click="open = !open">{{ open ? '取消' : '新增学生' }}</button>
    </div>

    <p v-if="props.error" class="error">{{ props.error }}</p>
    <form v-if="open" class="student-form" @submit.prevent="save">
      <label>姓名<input v-model="form.name" required maxlength="100" placeholder="例如：小明" /></label>
      <label>年级<input v-model="form.grade" maxlength="30" placeholder="例如：初一" /></label>
      <label>性别<input v-model="form.gender" maxlength="30" placeholder="可选" /></label>
      <label>学校<input v-model="form.school" maxlength="200" placeholder="可选" /></label>
      <button type="submit" :disabled="props.saving || !form.name.trim()">{{ props.saving ? '保存中…' : (editingId === null ? '保存学生' : '保存修改') }}</button>
    </form>

    <p v-if="props.students.length === 0" class="muted">暂无学生资料。添加后会作为 AI 分析上下文。</p>
    <ul v-else class="student-list">
      <li v-for="student in props.students" :key="student.id">
        <strong>{{ student.name }}</strong>
        <span>{{ student.grade || '年级未填写' }} · {{ student.school || '学校未填写' }}</span>
        <div class="student-actions"><button type="button" class="secondary" @click="startEdit(student)">编辑</button><button type="button" class="danger" @click="emit('archive', student.id)">归档</button></div>
      </li>
    </ul>
    <details v-if="props.archivedStudents.length" class="archived-list"><summary>已归档学生（{{ props.archivedStudents.length }}）</summary><div v-for="student in props.archivedStudents" :key="student.id" class="archived-item"><span>{{ student.name }} · {{ student.grade || '年级未填写' }}</span><button type="button" class="secondary" @click="emit('restore', student.id)">恢复</button></div></details>
  </section>
</template>

<style scoped>
.panel { padding: 22px; border: 1px solid #e2e8f0; border-radius: 16px; background: white; }
.panel-heading { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.eyebrow { margin: 0 0 6px; color: #0f766e; font-size: 12px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; }
h2 { margin: 0 0 16px; }
button { padding: 8px 12px; border: 0; border-radius: 8px; color: white; background: #0f766e; cursor: pointer; }
button:disabled { cursor: not-allowed; opacity: .5; }
.student-form { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; margin-bottom: 16px; }
label { display: grid; gap: 5px; color: #475569; font-size: 13px; }
input { width: 100%; box-sizing: border-box; padding: 9px; border: 1px solid #cbd5e1; border-radius: 8px; font: inherit; }
.student-form button { grid-column: 1 / -1; justify-self: start; }
.student-list { display: grid; gap: 8px; padding: 0; margin: 0; list-style: none; }
.student-list li { display: grid; gap: 4px; padding: 12px; border-radius: 10px; background: #f0fdfa; }
.student-actions { display: flex; gap: 8px; margin-top: 6px; }.student-actions button { padding: 6px 9px; }.secondary { color: #0f766e; background: #ccfbf1; }.danger { background: #be123c; }
.archived-list { margin-top: 14px; color: #64748b; font-size: 13px; }.archived-list summary { cursor: pointer; }.archived-item { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-top: 8px; padding: 8px; border-radius: 8px; background: #f8fafc; }.archived-item button { padding: 6px 9px; }
.student-list span, .muted { color: #64748b; font-size: 13px; }
.error { color: #dc2626; }
@media (max-width: 560px) { .student-form { grid-template-columns: 1fr; } }
</style>
