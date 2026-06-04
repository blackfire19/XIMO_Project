<template>
  <div>
    <div class="page-header">
      <a-typography-title :level="4" style="margin: 0">客户管理</a-typography-title>
      <a-button
        v-if="auth.hasRole('salesperson', 'super_admin')"
        type="primary"
        @click="openCreate"
      >
        <template #icon><plus-outlined /></template>
        新建客户
      </a-button>
    </div>

    <!-- 搜索栏 -->
    <a-card size="small" style="margin-bottom: 16px">
      <a-row :gutter="12" align="middle">
        <a-col :span="5">
          <a-input v-model:value="search.company_name" placeholder="公司名称" allow-clear @pressEnter="doSearch" />
        </a-col>
        <a-col :span="5">
          <a-input v-model:value="search.country" placeholder="国家" allow-clear @pressEnter="doSearch" />
        </a-col>
        <a-col :span="5">
          <a-input v-model:value="search.contact_name" placeholder="联系人" allow-clear @pressEnter="doSearch" />
        </a-col>
        <a-col :span="5">
          <a-input v-model:value="search.contact" placeholder="邮箱 / 电话" allow-clear @pressEnter="doSearch" />
        </a-col>
        <a-col :span="4">
          <a-space>
            <a-button type="primary" @click="doSearch">查询</a-button>
            <a-button @click="resetSearch">重置</a-button>
          </a-space>
        </a-col>
      </a-row>
    </a-card>

    <a-table
      :columns="columns"
      :data-source="customers"
      :loading="loading"
      row-key="id"
      :pagination="{
        current: currentPage,
        pageSize: pageSize,
        total: total,
        showTotal: (t) => `共 ${t} 条`,
        onChange: onPageChange,
        showSizeChanger: false,
      }"
      @row-click="(record) => goDetail(record.id)"
      :row-class-name="() => 'clickable-row'"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'company_name'">
          <a @click.stop="goDetail(record.id)">{{ record.company_name }}</a>
        </template>

        <template v-else-if="column.key === 'grade'">
          <a-tag :color="gradeColor(record.grade)">{{ gradeLabel(record.grade) }}</a-tag>
        </template>

        <template v-else-if="column.key === 'follow_freq'">
          <a-tag :color="freqColor(record.follow_freq)">{{ freqLabel(record.follow_freq) }}</a-tag>
        </template>

        <template v-else-if="column.key === 'owner'">
          {{ record.owner.full_name }}
        </template>

        <template v-else-if="column.key === 'actions'">
          <a-space @click.stop>
            <a-button
              v-if="canEdit(record)"
              size="small"
              @click="openEdit(record)"
            >编辑</a-button>
          </a-space>
        </template>
      </template>
    </a-table>

    <!-- 新建/编辑弹窗 -->
    <a-modal
      v-model:open="modalVisible"
      :title="editingCustomer ? '编辑客户' : '新建客户'"
      :confirm-loading="saving"
      @ok="handleSubmit"
      @cancel="resetForm"
    >
      <a-form ref="formRef" :model="form" :rules="rules" layout="vertical" style="margin-top: 16px">
        <a-form-item label="公司名称" name="company_name">
          <a-input v-model:value="form.company_name" />
        </a-form-item>

        <a-form-item label="国家" name="country">
          <a-input v-model:value="form.country" />
        </a-form-item>

        <a-form-item label="联系人" name="contact_name">
          <a-input v-model:value="form.contact_name" />
        </a-form-item>

        <a-form-item label="邮箱" name="email">
          <a-input v-model:value="form.email" />
        </a-form-item>

        <a-form-item label="电话">
          <a-input v-model:value="form.phone" />
        </a-form-item>

        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="贸易条款">
              <a-select v-model:value="form.trade_terms" allow-clear placeholder="请选择">
                <a-select-option v-for="t in TRADE_TERMS" :key="t" :value="t">{{ t }}</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="付款方式">
              <a-input v-model:value="form.payment_terms" placeholder="如 T/T 30 days" />
            </a-form-item>
          </a-col>
        </a-row>

        <a-form-item label="客户分级" name="grade">
          <a-radio-group v-model:value="form.grade">
            <a-radio-button value="key">重点</a-radio-button>
            <a-radio-button value="normal">普通</a-radio-button>
            <a-radio-button value="potential">潜在</a-radio-button>
          </a-radio-group>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { PlusOutlined } from '@ant-design/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { customersApi } from '@/api/customers'

const TRADE_TERMS = ['EXW', 'FOB', 'CFR', 'CIF', 'DAP', 'DDP']

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const customers = ref([])
const loading = ref(false)
const total = ref(0)
const currentPage = ref(1)
const pageSize = 10
const search = reactive({ company_name: '', country: '', contact_name: '', contact: '' })
const saving = ref(false)
const modalVisible = ref(false)
const editingCustomer = ref(null)
const formRef = ref()

const form = reactive({
  company_name: '',
  country: '',
  contact_name: '',
  email: '',
  phone: '',
  trade_terms: undefined,
  payment_terms: '',
  grade: 'potential',
})

const rules = {
  company_name: [{ required: true, message: '请输入公司名称' }],
  country: [{ required: true, message: '请输入国家' }],
  contact_name: [{ required: true, message: '请输入联系人' }],
}

const columns = [
  { title: '公司名称', key: 'company_name' },
  { title: '国家', dataIndex: 'country', key: 'country' },
  { title: '联系人', dataIndex: 'contact_name', key: 'contact_name' },
  { title: '邮箱', dataIndex: 'email', key: 'email' },
  { title: '分级', key: 'grade', width: 80 },
  { title: '跟进频次', key: 'follow_freq', width: 100 },
  { title: '负责人', key: 'owner', width: 100 },
  { title: '操作', key: 'actions', width: 80 },
]

function gradeColor(g) {
  return { key: 'red', normal: 'blue', potential: 'default' }[g] || 'default'
}
function gradeLabel(g) {
  return { key: '重点', normal: '普通', potential: '潜在' }[g] || g
}
function freqColor(f) {
  return { daily: 'green', weekly: 'blue', monthly: 'orange' }[f] || 'default'
}
function freqLabel(f) {
  return { daily: '每日', weekly: '每周', monthly: '每月' }[f] || f
}

function canEdit(record) {
  if (auth.hasRole('super_admin')) return true
  return auth.user?.id === record.owner.id
}

function goDetail(id) {
  router.push(`/customers/${id}`)
}

function buildParams(page = currentPage.value) {
  const params = { page, page_size: pageSize }
  if (search.company_name) params.company_name = search.company_name
  if (search.country) params.country = search.country
  if (search.contact_name) params.contact_name = search.contact_name
  if (search.contact) params.contact = search.contact
  return params
}

async function loadData(page = currentPage.value) {
  loading.value = true
  try {
    const res = await customersApi.list(buildParams(page))
    customers.value = res.data.items
    total.value = res.data.total
    currentPage.value = res.data.page
  } finally {
    loading.value = false
  }
}

function doSearch() {
  loadData(1)
}

function resetSearch() {
  search.company_name = ''
  search.country = ''
  search.contact_name = ''
  search.contact = ''
  loadData(1)
}

function onPageChange(page) {
  loadData(page)
}

function openCreate() {
  editingCustomer.value = null
  resetForm()
  modalVisible.value = true
}

function openEdit(record) {
  editingCustomer.value = record
  form.company_name = record.company_name
  form.country = record.country
  form.contact_name = record.contact_name
  form.email = record.email || ''
  form.phone = record.phone || ''
  form.trade_terms = record.trade_terms || undefined
  form.payment_terms = record.payment_terms || ''
  form.grade = record.grade
  modalVisible.value = true
}

function resetForm() {
  form.company_name = ''
  form.country = ''
  form.contact_name = ''
  form.email = ''
  form.phone = ''
  form.trade_terms = undefined
  form.payment_terms = ''
  form.grade = 'potential'
  formRef.value?.clearValidate()
}

async function handleSubmit() {
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  saving.value = true
  try {
    const payload = {
      company_name: form.company_name,
      country: form.country,
      contact_name: form.contact_name,
      email: form.email || null,
      phone: form.phone || null,
      trade_terms: form.trade_terms || null,
      payment_terms: form.payment_terms || null,
      grade: form.grade,
    }

    if (editingCustomer.value) {
      await customersApi.update(editingCustomer.value.id, payload)
      message.success('客户信息已更新')
    } else {
      await customersApi.create(payload)
      message.success('客户已创建')
    }

    modalVisible.value = false
    await loadData(1)
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
:deep(.clickable-row) {
  cursor: pointer;
}
</style>
