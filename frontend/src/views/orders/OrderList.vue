<template>
  <div>
    <div class="page-header">
      <a-typography-title :level="4" style="margin: 0">订单管理</a-typography-title>
    </div>

    <a-card size="small" style="margin-bottom: 16px">
      <a-row :gutter="12" align="middle">
        <a-col :span="5">
          <a-input v-model:value="search.so_number" placeholder="SO 编号" allow-clear @pressEnter="doSearch" />
        </a-col>
        <a-col :span="5">
          <a-select v-model:value="search.status" placeholder="状态" allow-clear style="width: 100%">
            <a-select-option v-for="s in STATUS_OPTIONS" :key="s.value" :value="s.value">
              {{ s.label }}
            </a-select-option>
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
      :data-source="orders"
      :loading="loading"
      row-key="id"
      :pagination="{ pageSize: 20, showTotal: (t) => `共 ${t} 条` }"
      @row-click="(record) => goDetail(record.id)"
      :row-class-name="() => 'clickable-row'"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'status'">
          <a-tag :color="statusColor(record.status)">{{ statusLabel(record.status) }}</a-tag>
        </template>
        <template v-else-if="column.key === 'customer'">
          {{ record.customer.company_name }}
        </template>
        <template v-else-if="column.key === 'salesperson'">
          {{ record.salesperson.full_name }}
        </template>
        <template v-else-if="column.key === 'est_ready_date'">
          <span v-if="record.est_ready_date && record.status === 'production'">
            {{ record.est_ready_date }}
            <a-tag color="orange" style="margin-left:4px">{{ countdownDays(record.est_ready_date) }}</a-tag>
          </span>
          <span v-else>{{ record.est_ready_date || '-' }}</span>
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
import { ref, reactive, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { orderApi } from '@/api/orders'

const STATUS_OPTIONS = [
  { value: 'confirmed', label: '已确认' },
  { value: 'production', label: '生产备货中' },
  { value: 'ready', label: '待出运' },
  { value: 'shipped', label: '已出运' },
  { value: 'completed', label: '已完结' },
]

const router = useRouter()
const route = useRoute()
const orders = ref([])
const loading = ref(false)
const search = reactive({ so_number: '', status: undefined })

const columns = [
  { title: 'SO 编号', dataIndex: 'so_number', key: 'so_number' },
  { title: '客户', key: 'customer' },
  { title: '业务员', key: 'salesperson' },
  { title: '贸易条款', dataIndex: 'trade_terms', key: 'trade_terms', width: 100 },
  { title: '预计备货完成', key: 'est_ready_date', width: 150 },
  { title: '状态', key: 'status', width: 110 },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 160 },
  { title: '操作', key: 'actions', width: 80 },
]

const STATUS_COLOR = {
  confirmed: 'blue',
  production: 'orange',
  ready: 'cyan',
  shipped: 'purple',
  completed: 'green',
}
const STATUS_LABEL = {
  confirmed: '已确认',
  production: '生产备货中',
  ready: '待出运',
  shipped: '已出运',
  completed: '已完结',
}

function statusColor(s) { return STATUS_COLOR[s] || 'default' }
function statusLabel(s) { return STATUS_LABEL[s] || s }

function countdownDays(dateStr) {
  const diff = Math.ceil((new Date(dateStr) - new Date()) / 86400000)
  if (diff < 0) return `已逾期 ${-diff} 天`
  if (diff === 0) return '今天'
  return `还有 ${diff} 天`
}

function goDetail(id) { router.push(`/orders/${id}`) }

async function loadData(params = {}) {
  loading.value = true
  try {
    const res = await orderApi.list(params)
    orders.value = res.data
  } finally {
    loading.value = false
  }
}

function doSearch() {
  const params = {}
  if (search.so_number) params.so_number = search.so_number
  if (search.status) params.status = search.status
  if (route.query.active === '1' && !search.status) params.active = true
  loadData(params)
}

function resetSearch() {
  search.so_number = ''
  search.status = undefined
  loadData()
}

function applyRouteQuery() {
  const params = {}
  if (route.query.status) {
    search.status = route.query.status
    params.status = route.query.status
  } else {
    search.status = undefined
  }
  if (route.query.active === '1') {
    params.active = true
  }
  loadData(params)
}

onMounted(applyRouteQuery)

// 路由 query 变化时重新加载（从看板跳转时生效）
watch(() => route.query, applyRouteQuery)
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
