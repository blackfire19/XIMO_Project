<template>
  <div>
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px">
      <a-typography-title :level="4" style="margin:0">正式订单</a-typography-title>
    </div>

    <a-row :gutter="12" style="margin-bottom:16px">
      <a-col :span="6">
        <a-input-search
          v-model:value="filters.so_number"
          placeholder="搜索订单号"
          allow-clear
          @search="loadData"
          @clear="loadData"
        />
      </a-col>
      <a-col :span="5">
        <a-select v-model:value="filters.status" placeholder="状态" allow-clear style="width:100%" @change="loadData">
          <a-select-option v-for="(label, key) in STATUS_LABEL" :key="key" :value="key">{{ label }}</a-select-option>
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
        <template v-if="column.key === 'so_number'">
          <a @click="goDetail(record.id)">{{ record.so_number }}</a>
        </template>
        <template v-else-if="column.key === 'customer'">{{ record.customer.company_name }}</template>
        <template v-else-if="column.key === 'salesperson'">{{ record.salesperson.full_name }}</template>
        <template v-else-if="column.key === 'is_stock'">
          <a-tag :color="record.is_stock ? 'blue' : 'gold'">{{ record.is_stock ? '现货' : '非现货' }}</a-tag>
        </template>
        <template v-else-if="column.key === 'status'">
          <a-tag :color="STATUS_COLOR[record.status]">{{ STATUS_LABEL[record.status] }}</a-tag>
        </template>
      </template>
    </a-table>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { formalOrdersApi } from '@/api/inquiries'

const router = useRouter()
const route = useRoute()

const STATUS_LABEL = {
  confirmed: '已确认', production: '生产中', ready: '待出运',
  shipping: '出运中', completed: '已完结',
}
const STATUS_COLOR = {
  confirmed: 'blue', production: 'gold', ready: 'orange',
  shipping: 'cyan', completed: 'green',
}

const columns = [
  { title: '订单号', dataIndex: 'so_number', key: 'so_number' },
  { title: '客户', key: 'customer' },
  { title: '业务员', key: 'salesperson' },
  { title: '货物', key: 'is_stock' },
  { title: '状态', dataIndex: 'status', key: 'status' },
  { title: '预计生产完成', dataIndex: 'est_production_date', key: 'est_production_date',
    customRender: ({ text }) => text || '—' },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at',
    customRender: ({ text }) => (text || '').slice(0, 10) },
]

const loading = ref(false)
const rows = ref([])
const filters = ref({ so_number: '', status: null })

async function loadData() {
  loading.value = true
  try {
    const params = {}
    if (filters.value.so_number) params.so_number = filters.value.so_number
    if (filters.value.status) params.status = filters.value.status
    if (route.query.active === '1' && !filters.value.status) params.active = true
    const res = await formalOrdersApi.list(params)
    rows.value = res.data
  } finally {
    loading.value = false
  }
}

function goDetail(id) {
  router.push({ name: 'OrderDetail', params: { id } })
}

function applyRouteQuery() {
  filters.value.status = route.query.status || null
  loadData()
}

onMounted(applyRouteQuery)
watch(() => route.query, applyRouteQuery)
</script>
