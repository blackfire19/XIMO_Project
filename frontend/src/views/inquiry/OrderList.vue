<template>
  <div>
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px">
      <a-typography-title :level="4" style="margin:0">正式订单</a-typography-title>
    </div>

    <!-- 老板/超管筛选区：第一行常用筛选，第二行搜索订单号 -->
    <template v-if="isBossOrAdmin">
      <a-row :gutter="12" style="margin-bottom:8px">
        <a-col :span="5">
          <a-select v-model:value="filters.has_accounting" placeholder="记账状态" allow-clear style="width:100%" @change="() => reload()">
            <a-select-option :value="true">已记账</a-select-option>
            <a-select-option :value="false">未记账</a-select-option>
          </a-select>
        </a-col>
        <a-col :span="5">
          <a-select v-model:value="filters.salary_calculated" placeholder="工资发放" allow-clear style="width:100%" @change="() => reload()">
            <a-select-option :value="true">已发放</a-select-option>
            <a-select-option :value="false">未发放</a-select-option>
          </a-select>
        </a-col>
        <a-col :span="5">
          <a-select v-model:value="filters.status" placeholder="状态" allow-clear style="width:100%" @change="() => reload()">
            <a-select-option v-for="(label, key) in STATUS_LABEL" :key="key" :value="key">{{ label }}</a-select-option>
          </a-select>
        </a-col>
        <a-col :span="5">
          <a-select v-model:value="filters.salesperson_id" placeholder="业务员" allow-clear style="width:100%" @change="() => reload()">
            <a-select-option v-for="u in salespersonList" :key="u.id" :value="u.id">{{ u.full_name }}</a-select-option>
          </a-select>
        </a-col>
      </a-row>
      <a-row :gutter="12" style="margin-bottom:16px">
        <a-col :span="8">
          <a-input-search
            v-model:value="filters.so_number"
            placeholder="搜索订单号"
            allow-clear
            @search="() => reload()"
            @clear="() => reload()"
          />
        </a-col>
      </a-row>
    </template>

    <!-- 其他角色筛选区 -->
    <a-row v-else :gutter="12" style="margin-bottom:16px">
      <a-col :span="6">
        <a-input-search
          v-model:value="filters.so_number"
          placeholder="搜索订单号"
          allow-clear
          @search="() => reload()"
          @clear="() => reload()"
        />
      </a-col>
      <a-col :span="5">
        <a-select v-model:value="filters.status" placeholder="状态" allow-clear style="width:100%" @change="() => reload()">
          <a-select-option v-for="(label, key) in STATUS_LABEL" :key="key" :value="key">{{ label }}</a-select-option>
        </a-select>
      </a-col>
      <!-- 财务专用筛选 -->
      <template v-if="isFinance">
        <a-col :span="4">
          <a-select v-model:value="filters.has_accounting" placeholder="是否记账" allow-clear style="width:100%" @change="() => reload()">
            <a-select-option :value="true">已记账</a-select-option>
            <a-select-option :value="false">未记账</a-select-option>
          </a-select>
        </a-col>
        <a-col :span="4">
          <a-select v-model:value="filters.salary_calculated" placeholder="是否发放工资" allow-clear style="width:100%" @change="() => reload()">
            <a-select-option :value="true">已发放</a-select-option>
            <a-select-option :value="false">未发放</a-select-option>
          </a-select>
        </a-col>
        <a-col :span="5">
          <a-select v-model:value="filters.salesperson_id" placeholder="业务员" allow-clear style="width:100%" @change="() => reload()">
            <a-select-option v-for="u in salespersonList" :key="u.id" :value="u.id">{{ u.full_name }}</a-select-option>
          </a-select>
        </a-col>
      </template>
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
          <a @click="goDetail(record.id)">{{ record.subject || record.so_number }}</a>
          <div v-if="record.subject" style="color:#bbb; font-size:12px">{{ record.so_number }}</div>
        </template>
        <template v-else-if="column.key === 'customer'">{{ fmtCustomer(record.customer.contact_name, record.customer.company_name) }}</template>
        <template v-else-if="column.key === 'salesperson'">{{ record.salesperson.full_name }}</template>
        <template v-else-if="column.key === 'is_stock'">
          <a-tag :color="record.is_stock ? 'blue' : 'gold'">{{ record.is_stock ? '现货' : '非现货' }}</a-tag>
        </template>
        <template v-else-if="column.key === 'status'">
          <a-tag :color="STATUS_COLOR[record.status]">{{ STATUS_LABEL[record.status] }}</a-tag>
        </template>
        <template v-else-if="column.key === 'bl_info'">
          <span v-if="record.bl_carrier && record.bl_number">{{ record.bl_carrier }}：{{ record.bl_number }}</span>
          <span v-else style="color:#bbb">—</span>
        </template>
        <template v-else-if="column.key === 'salary_calculated'">
          <a-tag v-if="record.profit != null" :color="record.salary_calculated ? 'green' : 'orange'">
            {{ record.salary_calculated ? '已发放' : '未发放' }}
          </a-tag>
          <span v-else style="color:#bbb">—</span>
        </template>
        <template v-else-if="column.key === 'profit'">
          <span v-if="record.profit != null" :style="{ fontWeight: 600, color: record.profit >= 0 ? '#52c41a' : '#ff4d4f' }">
            {{ record.profit.toFixed(2) }}
          </span>
          <span v-else style="color:#bbb">—</span>
        </template>
        <template v-else-if="column.key === 'action'">
          <a-button v-if="canEvaluate && !evaluatedIds.has(record.id)" size="small" type="primary" ghost @click="openQuickEval(record)">评价</a-button>
          <span v-else-if="canEvaluate" style="color:#bbb;font-size:12px">已评</span>
        </template>
      </template>

      <!-- 利润汇总行 -->
      <template v-if="profitTotal != null || profitGrandTotal != null" #summary>
        <!-- 本页合计 -->
        <a-table-summary-row v-if="profitTotal != null">
          <a-table-summary-cell :index="0" align="left" style="padding-left:8px; color:#e85555; font-weight:700">
            本页合计
          </a-table-summary-cell>
          <a-table-summary-cell v-for="(col, i) in columns.slice(1)" :key="col.key" :index="i + 1"
            :align="col.key === 'profit' ? 'right' : 'left'"
            :style="col.key === 'profit' ? 'padding-right:8px; white-space:nowrap' : ''"
          >
            <span v-if="col.key === 'profit'"
              :style="{ fontWeight: 700, fontSize: '14px', color: profitTotal >= 0 ? '#52c41a' : '#ff4d4f', whiteSpace: 'nowrap' }"
            >{{ profitTotal.toFixed(2) }}</span>
          </a-table-summary-cell>
        </a-table-summary-row>
        <!-- 汇总合计（全量） -->
        <a-table-summary-row v-if="profitGrandTotal != null">
          <a-table-summary-cell :index="0" align="left" style="padding-left:8px; color:#e85555; font-weight:700">
            汇总合计
          </a-table-summary-cell>
          <a-table-summary-cell v-for="(col, i) in columns.slice(1)" :key="col.key" :index="i + 1"
            :align="col.key === 'profit' ? 'right' : 'left'"
            :style="col.key === 'profit' ? 'padding-right:8px; white-space:nowrap' : ''"
          >
            <span v-if="col.key === 'profit'"
              :style="{ fontWeight: 700, fontSize: '14px', color: profitGrandTotal >= 0 ? '#52c41a' : '#ff4d4f', whiteSpace: 'nowrap' }"
            >{{ profitGrandTotal.toFixed(2) }}</span>
          </a-table-summary-cell>
        </a-table-summary-row>
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
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { formalOrdersApi } from '@/api/inquiries'
import { evaluationsApi } from '@/api/evaluations'
import { usersApi } from '@/api/users'
import { useAuthStore } from '@/stores/auth'
import { fmtCustomer } from '@/utils/format'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const canEvaluate = auth.hasRole('boss', 'super_admin')
const isFinance = auth.hasRole('finance')
const isBossOrAdmin = auth.hasRole('boss', 'super_admin')
const canFilterBySalesperson = auth.hasRole('boss', 'super_admin', 'finance')

const STATUS_LABEL = {
  confirmed: '已确认', production: '生产中', ready: '待出运',
  shipping: '出运中', completed: '已完结',
}
const STATUS_COLOR = {
  confirmed: 'blue', production: 'gold', ready: 'orange',
  shipping: 'cyan', completed: 'green',
}

// 列定义
const baseColumns = [
  { title: '主题 / 订单号', dataIndex: 'so_number', key: 'so_number' },
  { title: '客户', key: 'customer' },
  { title: '业务员', key: 'salesperson' },
]
const normalColumns = [
  { title: '货物', key: 'is_stock' },
  { title: '状态', dataIndex: 'status', key: 'status' },
  { title: '预计生产完成', dataIndex: 'est_production_date', key: 'est_production_date',
    customRender: ({ text }) => text || '—' },
]
const timeColumn = { title: '创建时间', dataIndex: 'created_at', key: 'created_at',
  customRender: ({ text }) => (text || '').slice(0, 10) }
const blColumn = { title: '提单信息', key: 'bl_info' }
const profitColumn = { title: '利润（CNY）', key: 'profit', width: 140, align: 'right' }
const salaryColumn = { title: '工资发放', key: 'salary_calculated', width: 90, align: 'center' }
const actionColumn = { title: '操作', key: 'action', width: 80 }

const columns = computed(() => [
  ...baseColumns,
  ...(isFinance ? [] : normalColumns),
  blColumn,
  timeColumn,
  profitColumn,
  ...(isFinance || isBossOrAdmin ? [salaryColumn] : []),
  ...(canEvaluate ? [actionColumn] : []),
])

// 利润列在 columns 中的索引（用于 summary colSpan）
const profitColIndex = computed(() => columns.value.findIndex(c => c.key === 'profit'))

// 利润汇总
const profitTotal = computed(() => {
  const withProfit = rows.value.filter(r => r.profit != null)
  if (withProfit.length === 0) return null
  return withProfit.reduce((s, r) => s + r.profit, 0)
})

// 业务员列表（财务筛选用）
const salespersonList = ref([])
async function loadSalespersons() {
  if (!canFilterBySalesperson) return
  const res = await usersApi.salespersons()
  salespersonList.value = res.data
}

// 评价
const evaluatedIds = ref(new Set())
async function loadEvaluatedIds() {
  if (!canEvaluate) return
  const res = await evaluationsApi.list({ target_type: 'formal_order' })
  evaluatedIds.value = new Set(res.data.map(e => e.target_id))
}

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

// 数据加载
const loading = ref(false)
const rows = ref([])
const profitGrandTotal = ref(null)   // 汇总合计（全量）
const filters = ref({
  so_number: '',
  status: isFinance ? 'completed' : null,  // 财务默认显示已完结
  has_accounting: isBossOrAdmin ? true : null,  // 老板/超管默认显示已核算利润
  salary_calculated: isBossOrAdmin ? false : null,  // 老板/超管默认显示未发工资
  salesperson_id: null,
})
const pagination = ref({ current: 1, pageSize: 10, total: 0, showTotal: t => `共 ${t} 条` })

async function loadData(page = 1) {
  loading.value = true
  try {
    const params = { page, page_size: pagination.value.pageSize }
    if (filters.value.so_number) params.so_number = filters.value.so_number
    if (filters.value.status) params.status = filters.value.status
    if (route.query.active === '1' && !filters.value.status) params.active = true
    if (isFinance || isBossOrAdmin) {
      if (filters.value.has_accounting != null) params.has_accounting = filters.value.has_accounting
    }
    if (isFinance || isBossOrAdmin) {
      if (filters.value.salary_calculated != null) params.salary_calculated = filters.value.salary_calculated
    }
    if (canFilterBySalesperson && filters.value.salesperson_id) {
      params.salesperson_id = filters.value.salesperson_id
    }
    const res = await formalOrdersApi.list(params)
    rows.value = res.data.items
    profitGrandTotal.value = res.data.profit_total ?? null
    pagination.value = { ...pagination.value, current: page, total: res.data.total }
    loadEvaluatedIds()
  } finally {
    loading.value = false
  }
}

function reload() { loadData(1) }

function onTableChange(pag) { loadData(pag.current) }

function goDetail(id) { router.push({ name: 'OrderDetail', params: { id } }) }

function parseTriBool(v) {
  return v === 'true' ? true : v === 'false' ? false : null
}

function applyRouteQuery() {
  const q = route.query
  if (isFinance) {
    if (q.has_accounting !== undefined) filters.value.has_accounting = parseTriBool(q.has_accounting)
    if (q.salary_calculated !== undefined) filters.value.salary_calculated = parseTriBool(q.salary_calculated)
  } else if (isBossOrAdmin) {
    // 跳转进入（带 query）按实际显示；直接进入（无 query）默认已记账+未发放
    const isJump = q.status !== undefined || q.has_accounting !== undefined
      || q.salary_calculated !== undefined || q.active !== undefined
    if (isJump) {
      filters.value.status = q.status || null
      filters.value.has_accounting = q.has_accounting !== undefined ? parseTriBool(q.has_accounting) : null
      filters.value.salary_calculated = q.salary_calculated !== undefined ? parseTriBool(q.salary_calculated) : null
    } else {
      filters.value.status = null
      filters.value.has_accounting = true
      filters.value.salary_calculated = false
    }
  } else {
    filters.value.status = q.status || null
  }
  loadData(1)
}

onMounted(() => {
  loadSalespersons()
  applyRouteQuery()
})
watch(() => route.query, applyRouteQuery)
</script>
