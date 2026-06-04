<template>
  <div>
    <div class="page-header">
      <a-typography-title :level="4" style="margin: 0">核价单</a-typography-title>
      <a-button
        v-if="auth.hasRole('salesperson', 'super_admin')"
        type="primary"
        @click="goCreate"
      >
        <template #icon><plus-outlined /></template>
        新建核价单
      </a-button>
    </div>

    <a-card size="small" style="margin-bottom: 16px">
      <a-row :gutter="12" align="middle">
        <a-col :span="6">
          <a-input v-model:value="search.ps_number" placeholder="核价单编号" allow-clear @pressEnter="doSearch" />
        </a-col>
        <a-col :span="5">
          <a-select v-model:value="search.status" placeholder="状态" allow-clear style="width: 100%">
            <a-select-option value="draft">草稿</a-select-option>
            <a-select-option value="confirmed">已确认</a-select-option>
            <a-select-option value="converted">已转PI</a-select-option>
          </a-select>
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
      :data-source="list"
      :loading="loading"
      row-key="id"
      :pagination="{ pageSize: 20, showTotal: (t) => `共 ${t} 条` }"
      @row-click="(r) => goDetail(r.id)"
      :row-class-name="() => 'clickable-row'"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'status'">
          <a-tag :color="statusColor(record.status)">{{ statusLabel(record.status) }}</a-tag>
        </template>
        <template v-else-if="column.key === 'customer'">
          {{ record.customer?.company_name || '-' }}
        </template>
        <template v-else-if="column.key === 'salesperson'">
          {{ record.salesperson.full_name }}
        </template>
        <template v-else-if="column.key === 'actions'">
          <a-space @click.stop>
            <a-button size="small" @click="goDetail(record.id)">详情</a-button>
          </a-space>
        </template>
      </template>
    </a-table>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { PlusOutlined } from '@ant-design/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { pricingSheetsApi } from '@/api/pricingSheets'

const auth = useAuthStore()
const router = useRouter()
const list = ref([])
const loading = ref(false)
const search = reactive({ ps_number: '', status: undefined })

const columns = [
  { title: '核价单编号', dataIndex: 'ps_number', key: 'ps_number' },
  { title: '客户', key: 'customer' },
  { title: '业务员', key: 'salesperson' },
  { title: '贸易条款', dataIndex: 'trade_terms', key: 'trade_terms', width: 100 },
  { title: '汇率', dataIndex: 'exchange_rate', key: 'exchange_rate', width: 80 },
  { title: '币种', dataIndex: 'currency', key: 'currency', width: 70 },
  { title: '状态', key: 'status', width: 90 },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 160 },
  { title: '操作', key: 'actions', width: 80 },
]

function statusColor(s) {
  return { draft: 'default', confirmed: 'blue', converted: 'green' }[s] || 'default'
}
function statusLabel(s) {
  return { draft: '草稿', confirmed: '已确认', converted: '已转PI' }[s] || s
}
function goCreate() { router.push('/pricing-sheets/new') }
function goDetail(id) { router.push(`/pricing-sheets/${id}`) }

async function loadData(params = {}) {
  loading.value = true
  try {
    const res = await pricingSheetsApi.list(params)
    list.value = res.data
  } finally {
    loading.value = false
  }
}
function doSearch() {
  const p = {}
  if (search.ps_number) p.ps_number = search.ps_number
  if (search.status) p.status = search.status
  loadData(p)
}
function resetSearch() {
  search.ps_number = ''
  search.status = undefined
  loadData()
}
onMounted(() => loadData())
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
:deep(.clickable-row) { cursor: pointer; }
</style>
