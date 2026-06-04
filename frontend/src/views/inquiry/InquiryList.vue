<template>
  <div>
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px">
      <a-typography-title :level="4" style="margin:0">询价单</a-typography-title>
      <a-button
        v-if="auth.hasRole('super_admin', 'salesperson')"
        type="primary"
        @click="openCreate"
      >
        新建询价单
      </a-button>
    </div>

    <a-row :gutter="12" style="margin-bottom:16px">
      <a-col :span="6">
        <a-input-search
          v-model:value="filters.enq_number"
          placeholder="搜索询价单号"
          allow-clear
          @search="loadData"
          @clear="loadData"
        />
      </a-col>
      <a-col :span="5">
        <a-select v-model:value="filters.status" placeholder="状态" allow-clear style="width:100%" @change="loadData">
          <a-select-option value="active">进行中</a-select-option>
          <a-select-option value="deposit_received">已收定金</a-select-option>
          <a-select-option value="converted">已转订单</a-select-option>
          <a-select-option value="void">已失效</a-select-option>
        </a-select>
      </a-col>
    </a-row>

    <a-table
      :columns="columns"
      :data-source="rows"
      :loading="loading"
      :pagination="{ pageSize: 20, showTotal: t => `共 ${t} 条` }"
      row-key="id"
      size="small"
      bordered
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'enq_number'">
          <a @click="goDetail(record.id)">{{ record.enq_number }}</a>
        </template>
        <template v-else-if="column.key === 'customer'">
          {{ record.customer.company_name }}
        </template>
        <template v-else-if="column.key === 'salesperson'">
          {{ record.salesperson.full_name }}
        </template>
        <template v-else-if="column.key === 'status'">
          <a-tag :color="STATUS_COLOR[record.status]">{{ STATUS_LABEL[record.status] }}</a-tag>
        </template>
        <template v-else-if="column.key === 'deposit_amount'">
          {{ record.deposit_amount != null ? Number(record.deposit_amount).toLocaleString() : '—' }}
        </template>
      </template>
    </a-table>

    <a-modal v-model:open="createOpen" title="新建询价单" :confirm-loading="creating" @ok="doCreate">
      <a-form layout="vertical">
        <a-form-item label="选择客户" required>
          <a-select
            v-model:value="form.customer_id"
            show-search
            placeholder="搜索客户公司名"
            :filter-option="false"
            :options="customerOptions"
            @search="searchCustomers"
          />
        </a-form-item>
        <a-form-item label="备注">
          <a-textarea v-model:value="form.remarks" :rows="3" placeholder="可选" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { inquiriesApi } from '@/api/inquiries'
import { customersApi } from '@/api/customers'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()

const STATUS_LABEL = {
  active: '进行中', deposit_received: '已收定金',
  converted: '已转订单', void: '已失效',
}
const STATUS_COLOR = {
  active: 'orange', deposit_received: 'green',
  converted: 'blue', void: 'default',
}

const columns = [
  { title: '询价单号', dataIndex: 'enq_number', key: 'enq_number' },
  { title: '客户', key: 'customer' },
  { title: '业务员', key: 'salesperson' },
  { title: '状态', dataIndex: 'status', key: 'status' },
  { title: '定金', dataIndex: 'deposit_amount', key: 'deposit_amount', align: 'right' },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at',
    customRender: ({ text }) => (text || '').slice(0, 10) },
]

const loading = ref(false)
const rows = ref([])
const filters = ref({ enq_number: '', status: null })

async function loadData() {
  loading.value = true
  try {
    const params = {}
    if (filters.value.enq_number) params.enq_number = filters.value.enq_number
    if (filters.value.status) params.status = filters.value.status
    const res = await inquiriesApi.list(params)
    rows.value = res.data
  } finally {
    loading.value = false
  }
}

function goDetail(id) {
  router.push({ name: 'InquiryDetail', params: { id } })
}

// ── 新建 ──
const createOpen = ref(false)
const creating = ref(false)
const form = ref({ customer_id: undefined, remarks: '' })
const customerOptions = ref([])

function openCreate() {
  form.value = { customer_id: undefined, remarks: '' }
  customerOptions.value = []
  createOpen.value = true
  fetchCustomers('')
}

let searchTimer = null
async function fetchCustomers(kw) {
  const res = await customersApi.list({ company_name: kw || undefined, page_size: 20 })
  const items = res.data?.items || []
  customerOptions.value = items.map((c) => ({
    value: c.id, label: `${c.company_name}（${c.country}）`,
  }))
}
function searchCustomers(kw) {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => fetchCustomers(kw), 300)
}

async function doCreate() {
  if (!form.value.customer_id) {
    message.warning('请选择客户')
    return
  }
  creating.value = true
  try {
    const res = await inquiriesApi.create({
      customer_id: form.value.customer_id,
      remarks: form.value.remarks || null,
    })
    message.success('创建成功')
    createOpen.value = false
    goDetail(res.data.id)
  } finally {
    creating.value = false
  }
}

onMounted(loadData)
</script>
