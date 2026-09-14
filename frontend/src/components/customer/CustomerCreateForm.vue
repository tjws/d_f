<script setup lang="ts">
import { reactive, ref } from 'vue'
import { createCustomer } from '../../api/customers'
import type { Customer, CustomerCreate } from '../../types/customer'

const emit = defineEmits<{
  created: [customer: Customer]
}>()

function createEmptyForm(): CustomerCreate {
  return {
    name: '',
    phone: '',
    student_name: '',
    grade: '',
    interested_subject: '',
    source: '',
    remark: '',
    stage: 'new',
  }
}

const form = reactive<CustomerCreate>(createEmptyForm())
const submitting = ref(false)
const errorMessage = ref('')

async function submitForm(): Promise<void> {
  errorMessage.value = ''

  if (!form.name.trim() || !form.phone.trim()) {
    errorMessage.value = '客户姓名和手机号不能为空'
    return
  }

  submitting.value = true

  try {
    const customer = await createCustomer({
      name: form.name.trim(),
      phone: form.phone.trim(),
      student_name: form.student_name?.trim() || null,
      grade: form.grade?.trim() || null,
      interested_subject: form.interested_subject?.trim() || null,
      source: form.source?.trim() || null,
      remark: form.remark?.trim() || null,
      stage: 'new',
    })

    emit('created', customer)
    Object.assign(form, createEmptyForm())
  } catch (error) {
    errorMessage.value =
      error instanceof Error ? error.message : '创建客户失败'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <form class="customer-form" @submit.prevent="submitForm">
    <h2>新建客户</h2>

    <label>
      客户姓名
      <input v-model="form.name" type="text" placeholder="例如：王老师" />
    </label>

    <label>
      手机号
      <input v-model="form.phone" type="text" placeholder="例如：13800138000" />
    </label>

    <label>
      学生姓名
      <input v-model="form.student_name" type="text" placeholder="可选" />
    </label>

    <label>
      年级
      <input v-model="form.grade" type="text" placeholder="例如：初二" />
    </label>

    <label>
      感兴趣的科目
      <input
        v-model="form.interested_subject"
        type="text"
        placeholder="例如：数学"
      />
    </label>

    <label>
      来源
      <input v-model="form.source" type="text" placeholder="例如：企业微信" />
    </label>

    <label>
      备注
      <textarea v-model="form.remark" rows="3" placeholder="可选" />
    </label>

    <p v-if="errorMessage" class="error-message">
      {{ errorMessage }}
    </p>

    <button type="submit" :disabled="submitting">
      {{ submitting ? '保存中...' : '保存客户' }}
    </button>
  </form>
</template>

<style scoped>
.customer-form {
  max-width: 960px;
  margin: 0 auto 24px;
  padding: 24px;
  border: 1px solid #bfdbfe;
  border-radius: 16px;
  background: #eff6ff;
}

.customer-form h2 {
  margin-top: 0;
}

.customer-form label {
  display: block;
  margin-bottom: 14px;
  color: #334155;
  font-weight: 600;
}

.customer-form input,
.customer-form textarea {
  display: block;
  box-sizing: border-box;
  width: 100%;
  margin-top: 6px;
  padding: 10px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font: inherit;
}

.customer-form button {
  padding: 10px 18px;
  border: 0;
  border-radius: 8px;
  color: white;
  background: #2563eb;
  cursor: pointer;
}

.customer-form button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.error-message {
  color: #dc2626;
}
</style>
