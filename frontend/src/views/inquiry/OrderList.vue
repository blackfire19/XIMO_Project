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
      :pagination="pagination"
      row-key="id"
      size="small"
      bordered
      @change="onTableChange"
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
        <template v-else-if="column.key === 'action'">
          <a-button v-if="canEvaluate && !evaluatedIds.has(record.id)" size="small" type="primary" ghost @click="openQuickEval(record)">评价</a-button>
          <span v-else-if="canEvaluate" style="color:#bbb;font-size:12px">已评</span>
        </template>
      </template>
    </a-table>

    <!-- 快捷评价弹窗 -->
    <a-modal
      v-model:open="quickEvalVisible"
      :title="`评价 ${quickEvalTarget?.salesperson?.full_name ?? ''}`"
      ok-text="提交评价"
      cancel-text="取消"
      :confirm-loading="quickEvalSubmitting"
      width="400px"
      @ok="submitQuickEval"
    >
      <a-form layout="vertical" style="margin-top: 8px">
        <a-form-item label="评分（1-10分）" required>
          <a-input-number
            v-model:value="quickEvalForm.score"
            :min="1" :max="10" :precision="0"
            style="width: 120px" placeholder="1-10"
          />
          <span style="margin-left: 8px; color: #999; font-size: 13px">/ 10 分</span>
        </a-form-item>
        <a-form-item label="评语（选填）">
          <a-textarea v-model:value="quickEvalForm.comment" :rows="3"
            placeholder="输入评语..." :maxlength="200" show-count />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { formalOrdersApi } from '@/api/inquiries'
import { evaluationsApi } from '@/api/evaluations'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const canEvaluate = auth.hasRole('boss', 'super_admin')

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
  ...(canEvaluate ? [{ title: '操作', key: 'action', width: 80 }] : []),
]

// 已评价记录 ID 集合
const evaluatedIds = ref(new Set())

async function loadEvaluatedIds() {
  if (!canEvaluate) return
  const res = await evaluationsApi.list({ target_type: 'formal_order' })
  evaluatedIds.value = new Set(res.data.map(e => e.target_id))
}

// 快捷评价
const quickEvalVisible = ref(false)
const quickEvalTarget = ref(null)
const quickEvalForm = ref({ score: null, comment: '' })
const quickEvalSubmitting = ref(false)

function openQuickEval(record) {
  quickEvalTarget.value = record
  quickEvalForm.value = { score: null, comment: '' }
  quickEvalVisible.value = true
}

async function submitQuickEval() {
  const s = quickEvalForm.value.score
  if (!s) { message.warning('请填写评分'); return }
  if (s < 1 || s > 10) { message.warning('评分须在 1-10 之间'); return }
  quickEvalSubmitting.value = true
  try {
    await evaluationsApi.create({
      target_type: 'formal_order',
      target_id: quickEvalTarget.value.id,
      subject_id: quickEvalTarget.value.salesperson.id,
      score: quickEvalForm.value.score,
      comment: quickEvalForm.value.comment || null,
    })
    message.success(`已对 ${quickEvalTarget.value.salesperson.full_name} 提交评价`)
    quickEvalVisible.value = false
    loadEvaluatedIds()
  } catch {
    message.error('提交失败')
  } finally {
    quickEvalSubmitting.value = false
  }
}

const loading = ref(false)
const rows = ref([])
const filters = ref({ so_number: '', status: null })
const pagination = ref({ current: 1, pageSize: 20, total: 0, showTotal: t => `共 ${t} 条` })

async function loadData(page = pagination.value.current) {
  loading.value = true
  try {
    const params = { page, page_size: pagination.value.pageSize }
    if (filters.value.so_number) params.so_number = filters.value.so_number
    if (filters.value.status) params.status = filters.value.status
    if (route.query.active === '1' && !filters.value.status) params.active = true
    const res = await formalOrdersApi.list(params)
    rows.value = res.data.items
    pagination.value = { ...pagination.value, current: page, total: res.data.total }
    loadEvaluatedIds()
  } finally {
    loading.value = false
  }
}

function onTableChange(pag) {
  loadData(pag.current)
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
