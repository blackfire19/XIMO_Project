<template>
  <div>
    <!-- 顶部操作栏 -->
    <div class="page-header">
      <a-space>
        <a-button @click="router.back()">返回</a-button>
        <a-typography-title :level="4" style="margin: 0">
          {{ isNew ? '新建报价单' : quotation?.pi_number }}
        </a-typography-title>
        <a-tag v-if="!isNew" :color="statusColor(quotation?.status)">
          {{ statusLabel(quotation?.status) }}
        </a-tag>
        <a-tooltip v-if="quotation?.pricing_sheet_id" title="点击查看来源核价单">
          <a-tag
            color="blue"
            style="cursor:pointer"
            @click="router.push(`/pricing-sheets/${quotation.pricing_sheet_id}`)"
          >
            来源：{{ sourcePsNumber || `核价单#${quotation.pricing_sheet_id}` }}
          </a-tag>
        </a-tooltip>
      </a-space>

      <a-space v-if="!isNew">
        <!-- 下载 PI -->
        <a-dropdown v-if="quotation?.status !== 'expired'">
          <a-button>
            下载 PI <down-outlined />
          </a-button>
          <template #overlay>
            <a-menu>
              <a-menu-item @click="downloadPI(false)">客户版 PDF</a-menu-item>
              <a-menu-item @click="downloadPI(true)">内部版 PDF</a-menu-item>
            </a-menu>
          </template>
        </a-dropdown>

        <template v-if="canEdit">
          <a-button
            v-if="quotation?.status === 'draft'"
            type="primary"
            :loading="saving"
            @click="handleSave"
          >保存</a-button>
          <a-popconfirm
            v-if="quotation?.status === 'draft'"
            title="确认发送该报价单？"
            @confirm="changeStatus('sent')"
          >
            <a-button>标记已发送</a-button>
          </a-popconfirm>
          <a-popconfirm
            v-if="quotation?.status === 'sent'"
            title="确认标记为已成交？"
            @confirm="changeStatus('won')"
          >
            <a-button type="primary">标记已成交</a-button>
          </a-popconfirm>
          <a-popconfirm
            v-if="quotation?.status === 'sent' || quotation?.status === 'draft'"
            title="确认作废该报价单？"
            @confirm="changeStatus('expired')"
          >
            <a-button danger>作废</a-button>
          </a-popconfirm>
          <a-popconfirm
            v-if="quotation?.status === 'won'"
            title="确认一键转单？"
            @confirm="handleConvert"
          >
            <a-button type="primary">一键转单</a-button>
          </a-popconfirm>
        </template>
      </a-space>

      <a-button
        v-if="isNew"
        type="primary"
        :loading="saving"
        @click="handleCreate"
      >创建报价单</a-button>
    </div>

    <a-spin :spinning="pageLoading">
      <a-row :gutter="16">
        <!-- 基本信息 -->
        <a-col :span="24">
          <a-card title="基本信息" size="small" style="margin-bottom: 16px">
            <a-form
              ref="formRef"
              :model="form"
              :rules="rules"
              layout="vertical"
              :disabled="!canEdit && !isNew"
            >
              <a-row :gutter="16">
                <a-col :span="6">
                  <a-form-item label="客户" name="customer_id">
                    <a-select
                      v-model:value="form.customer_id"
                      show-search
                      :filter-option="false"
                      placeholder="搜索客户名称"
                      :options="customerOptions"
                      @search="searchCustomers"
                      @change="onCustomerChange"
                    />
                  </a-form-item>
                </a-col>
                <a-col :span="4">
                  <a-form-item label="币种" name="currency">
                    <a-select v-model:value="form.currency">
                      <a-select-option value="USD">USD</a-select-option>
                      <a-select-option value="EUR">EUR</a-select-option>
                      <a-select-option value="CNY">CNY</a-select-option>
                    </a-select>
                  </a-form-item>
                </a-col>
                <a-col :span="4">
                  <a-form-item label="汇率">
                    <a-input-number v-model:value="form.exchange_rate" :precision="4" style="width: 100%" placeholder="可选" />
                  </a-form-item>
                </a-col>
                <a-col :span="4">
                  <a-form-item label="贸易条款">
                    <a-select v-model:value="form.trade_terms" allow-clear placeholder="请选择">
                      <a-select-option v-for="t in TRADE_TERMS" :key="t" :value="t">{{ t }}</a-select-option>
                    </a-select>
                  </a-form-item>
                </a-col>
                <a-col :span="3">
                  <a-form-item label="交货期">
                    <a-date-picker v-model:value="form.delivery_date" style="width: 100%" value-format="YYYY-MM-DD" />
                  </a-form-item>
                </a-col>
                <a-col :span="3">
                  <a-form-item label="有效期至">
                    <a-date-picker v-model:value="form.valid_until" style="width: 100%" value-format="YYYY-MM-DD" />
                  </a-form-item>
                </a-col>
              </a-row>
              <a-row :gutter="16">
                <a-col :span="6">
                  <a-form-item label="联系人 (ATTAN)">
                    <a-input v-model:value="form.contact_person" placeholder="业务员姓名" />
                  </a-form-item>
                </a-col>
                <a-col :span="9">
                  <a-form-item label="付款条件">
                    <a-input v-model:value="form.payment_terms" placeholder="如 30% deposit, 70% before shipment" />
                  </a-form-item>
                </a-col>
                <a-col :span="9">
                  <a-form-item label="品名 (COMMODITY)">
                    <a-input v-model:value="form.commodity" placeholder="如 HOT ROLLED STEEL SHEETS Q235" />
                  </a-form-item>
                </a-col>
              </a-row>
              <a-row :gutter="16">
                <a-col :span="6">
                  <a-form-item label="包装 (PACKING)">
                    <a-input v-model:value="form.packing" placeholder="EXPORT STANDARD" />
                  </a-form-item>
                </a-col>
                <a-col :span="9">
                  <a-form-item label="装运港">
                    <a-input v-model:value="form.port_of_loading" placeholder="如 TIANJIN XINGANG PORT OF CHINA" />
                  </a-form-item>
                </a-col>
                <a-col :span="9">
                  <a-form-item label="目的港 (FOR TRANSPORTATION TO)">
                    <a-input v-model:value="form.destination_port" placeholder="如 TAMATAVE Port" />
                  </a-form-item>
                </a-col>
              </a-row>
              <a-row :gutter="16">
                <a-col :span="12">
                  <a-form-item label="PI 备注 (NOTE)">
                    <a-textarea v-model:value="form.note_pi" :rows="2" placeholder="可选，显示在 PI 文件上" />
                  </a-form-item>
                </a-col>
                <a-col :span="12">
                  <a-form-item label="内部备注">
                    <a-textarea v-model:value="form.remarks" :rows="2" placeholder="系统内部备注，不显示在 PI 上" />
                  </a-form-item>
                </a-col>
              </a-row>
            </a-form>
          </a-card>
        </a-col>

        <!-- 产品明细 -->
        <a-col :span="24">
          <a-card size="small">
            <template #title>
              <span>产品明细</span>
            </template>
            <template #extra>
              <a-space v-if="canEdit || isNew">
                <a-button size="small" @click="openProductPicker">从产品库选择</a-button>
                <a-button size="small" @click="addCustomItem">自由填写</a-button>
              </a-space>
            </template>

            <a-table
              :columns="itemColumns"
              :data-source="form.items"
              :pagination="false"
              row-key="__key"
              size="small"
            >
              <template #bodyCell="{ column, record, index }">
                <template v-if="column.key === 'grade_label'">
                  <a-input
                    v-if="canEdit || isNew"
                    v-model:value="record.grade_label"
                    size="small"
                    placeholder="如 Q235"
                  />
                  <span v-else>{{ record.grade_label || '-' }}</span>
                </template>
                <template v-else-if="column.key === 'hscode'">
                  <a-input
                    v-if="canEdit || isNew"
                    v-model:value="record.hscode"
                    size="small"
                    placeholder="如 720851"
                  />
                  <span v-else>{{ record.hscode || '-' }}</span>
                </template>
                <template v-else-if="column.key === 'description'">
                  <a-input
                    v-if="canEdit || isNew"
                    v-model:value="record.description"
                    size="small"
                  />
                  <span v-else>{{ record.description }}</span>
                </template>
                <template v-else-if="column.key === 'quantity'">
                  <a-input-number
                    v-if="canEdit || isNew"
                    v-model:value="record.quantity"
                    :min="0"
                    :precision="3"
                    size="small"
                    style="width: 100%"
                  />
                  <span v-else>{{ record.quantity }}</span>
                </template>
                <template v-else-if="column.key === 'unit'">
                  <a-select
                    v-if="canEdit || isNew"
                    v-model:value="record.unit"
                    size="small"
                    style="width: 70px"
                  >
                    <a-select-option value="MT">MT</a-select-option>
                    <a-select-option value="PCS">PCS</a-select-option>
                    <a-select-option value="SET">SET</a-select-option>
                  </a-select>
                  <span v-else>{{ record.unit }}</span>
                </template>
                <template v-else-if="column.key === 'unit_price'">
                  <a-input-number
                    v-if="canEdit || isNew"
                    v-model:value="record.unit_price"
                    :min="0"
                    :precision="2"
                    size="small"
                    style="width: 100%"
                  />
                  <span v-else>{{ record.unit_price }}</span>
                </template>
                <template v-else-if="column.key === 'unit_price_internal'">
                  <a-input-number
                    v-if="canEdit || isNew"
                    v-model:value="record.unit_price_internal"
                    :min="0"
                    :precision="2"
                    size="small"
                    style="width: 100%"
                    placeholder="内部价"
                  />
                  <span v-else>{{ record.unit_price_internal ?? '-' }}</span>
                </template>
                <template v-else-if="column.key === 'amount'">
                  {{ ((record.quantity || 0) * (record.unit_price || 0)).toFixed(2) }}
                </template>
                <template v-else-if="column.key === 'actions'">
                  <a-button
                    v-if="canEdit || isNew"
                    size="small"
                    danger
                    @click="removeItem(index)"
                  >删除</a-button>
                </template>
              </template>

              <template #summary>
                <a-table-summary-row>
                  <a-table-summary-cell :col-span="5" align="right">
                    <strong>合计金额</strong>
                  </a-table-summary-cell>
                  <a-table-summary-cell>
                    <strong>{{ totalAmount }} {{ form.currency }}</strong>
                  </a-table-summary-cell>
                  <a-table-summary-cell />
                </a-table-summary-row>
              </template>
            </a-table>
          </a-card>
        </a-col>
      </a-row>
    </a-spin>


    <!-- 从产品库选择弹窗 -->
    <a-modal
      v-model:open="pickerVisible"
      title="从产品库选择"
      width="800px"
      :footer="null"
    >
      <a-input
        v-model:value="productSearch"
        placeholder="搜索规格/材质"
        style="margin-bottom: 12px"
        allow-clear
        @input="filterProducts"
      />
      <a-table
        :columns="productColumns"
        :data-source="filteredProducts"
        :loading="productsLoading"
        row-key="id"
        size="small"
        :pagination="{ pageSize: 10 }"
        :row-selection="{ selectedRowKeys: selectedProductIds, onChange: onProductSelect, type: 'checkbox' }"
      />
      <div style="margin-top: 12px; text-align: right">
        <a-button type="primary" @click="confirmProductPick">
          添加选中产品（{{ selectedProductIds.length }}）
        </a-button>
      </div>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { DownOutlined } from '@ant-design/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { quotationsApi } from '@/api/quotations'
import { customersApi } from '@/api/customers'
import { productsApi } from '@/api/products'
import { pricingSheetsApi } from '@/api/pricingSheets'
import { api } from '@/api'

const TRADE_TERMS = ['EXW', 'FOB', 'CFR', 'CIF', 'DAP', 'DDP']

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const isNew = computed(() => route.params.id === 'new')
const quotationId = computed(() => isNew.value ? null : Number(route.params.id))

const quotation = ref(null)
const sourcePsNumber = ref('')  // 来源核价单编号
const pageLoading = ref(false)
const saving = ref(false)
const formRef = ref()

const form = reactive({
  customer_id: undefined,
  currency: 'USD',
  exchange_rate: null,
  trade_terms: undefined,
  delivery_date: null,
  valid_until: null,
  remarks: '',
  contact_person: '',
  payment_terms: '',
  commodity: '',
  packing: 'EXPORT STANDARD',
  port_of_loading: '',
  destination_port: '',
  note_pi: '',
  items: [],
})

const rules = {
  customer_id: [{ required: true, message: '请选择客户' }],
}

const canEdit = computed(() => {
  if (isNew.value) return true
  const role = auth.user?.role || ''
  if (role === 'super_admin') return true
  if (role === 'salesperson' && quotation.value?.salesperson?.id === auth.user?.id) {
    return quotation.value?.status === 'draft'
  }
  return false
})

// 客户搜索
const customerOptions = ref([])
const allCustomers = ref([])
async function loadCustomers() {
  const res = await customersApi.list({ page_size: 200 })
  const list = res.data.items ?? res.data
  allCustomers.value = list
  customerOptions.value = list.map((c) => ({
    value: c.id,
    label: `${c.company_name} (${c.country})`,
  }))
}
function searchCustomers(val) {
  customerOptions.value = allCustomers.value
    .filter((c) => c.company_name.toLowerCase().includes(val.toLowerCase()))
    .map((c) => ({ value: c.id, label: `${c.company_name} (${c.country})` }))
}

function onCustomerChange() {
  // 选择客户后可在此处做联动，如自动填入贸易条款
}

// 产品明细
let itemCounter = 0
function makeKey() { return ++itemCounter }

const itemColumns = [
  { title: '牌号 (GRADE)', key: 'grade_label', width: 100 },
  { title: 'HS编码', key: 'hscode', width: 100 },
  { title: '产品描述 (SIZE)', key: 'description', width: 220 },
  { title: '数量', key: 'quantity', width: 90 },
  { title: '单位', key: 'unit', width: 75 },
  { title: '客户单价', key: 'unit_price', width: 100 },
  { title: '内部单价', key: 'unit_price_internal', width: 100 },
  { title: '金额', key: 'amount', width: 100 },
  { title: '操作', key: 'actions', width: 65 },
]

const totalAmount = computed(() => {
  return form.items
    .reduce((sum, item) => sum + (item.quantity || 0) * (item.unit_price || 0), 0)
    .toFixed(2)
})

function addCustomItem() {
  form.items.push({
    __key: makeKey(),
    product_id: null,
    grade_label: '',
    hscode: '',
    description: '',
    quantity: 1,
    unit: 'MT',
    unit_price: 0,
    unit_price_internal: null,
    sort_order: form.items.length,
  })
}

function removeItem(index) {
  form.items.splice(index, 1)
}

// 产品库选择器
const pickerVisible = ref(false)
const productSearch = ref('')
const allProducts = ref([])
const filteredProducts = ref([])
const productsLoading = ref(false)
const selectedProductIds = ref([])
const selectedProducts = ref([])

const productColumns = [
  { title: '规格', dataIndex: 'spec', key: 'spec' },
  { title: '材质', dataIndex: 'material', key: 'material', width: 80 },
  { title: '产品类型', dataIndex: 'product_type', key: 'product_type', width: 100 },
  { title: '长度', dataIndex: 'length', key: 'length', width: 90 },
  { title: '参考单价', dataIndex: 'unit_price', key: 'unit_price', width: 100 },
  { title: '仓库', dataIndex: 'warehouse', key: 'warehouse', width: 90 },
]

async function openProductPicker() {
  pickerVisible.value = true
  selectedProductIds.value = []
  selectedProducts.value = []
  if (allProducts.value.length === 0) {
    productsLoading.value = true
    try {
      const res = await productsApi.list()
      allProducts.value = res.data
    } finally {
      productsLoading.value = false
    }
  }
  filteredProducts.value = allProducts.value
}

function filterProducts() {
  const kw = productSearch.value.toLowerCase()
  filteredProducts.value = kw
    ? allProducts.value.filter(
        (p) =>
          p.spec.toLowerCase().includes(kw) ||
          (p.material || '').toLowerCase().includes(kw)
      )
    : allProducts.value
}

function onProductSelect(keys, rows) {
  selectedProductIds.value = keys
  selectedProducts.value = rows
}

function confirmProductPick() {
  const base = form.items.length
  selectedProducts.value.forEach((p, i) => {
    form.items.push({
      __key: makeKey(),
      product_id: p.id,
      grade_label: p.material || '',
      hscode: '',
      description: `${p.spec}${p.length ? ' L=' + p.length : ''}`.trim(),
      quantity: 1,
      unit: 'MT',
      unit_price: p.unit_price ? Number(p.unit_price) : 0,
      unit_price_internal: null,
      sort_order: base + i,
    })
  })
  pickerVisible.value = false
}

// 状态
function statusColor(s) {
  return { draft: 'default', sent: 'blue', won: 'green', expired: 'red' }[s] || 'default'
}
function statusLabel(s) {
  return { draft: '草稿', sent: '已发送', won: '已成交', expired: '已失效' }[s] || s
}

// 加载详情
async function loadQuotation() {
  pageLoading.value = true
  try {
    const res = await quotationsApi.get(quotationId.value)
    quotation.value = res.data
    const q = res.data
    form.customer_id = q.customer.id
    form.currency = q.currency
    form.exchange_rate = q.exchange_rate ? Number(q.exchange_rate) : null
    form.trade_terms = q.trade_terms || undefined
    form.delivery_date = q.delivery_date || null
    form.valid_until = q.valid_until || null
    form.remarks = q.remarks || ''
    form.contact_person = q.contact_person || ''
    form.payment_terms = q.payment_terms || ''
    form.commodity = q.commodity || ''
    form.packing = q.packing || 'EXPORT STANDARD'
    form.port_of_loading = q.port_of_loading || ''
    form.destination_port = q.destination_port || ''
    form.note_pi = q.note_pi || ''
    if (q.pricing_sheet_id) {
      try {
        const psRes = await pricingSheetsApi.get(q.pricing_sheet_id)
        sourcePsNumber.value = psRes.data.ps_number
      } catch {}
    }
    form.items = (q.items || [])
      .sort((a, b) => a.sort_order - b.sort_order)
      .map((item) => ({
        ...item,
        __key: makeKey(),
        grade_label: item.grade_label || '',
        hscode: item.hscode || '',
        quantity: Number(item.quantity),
        unit_price: Number(item.unit_price),
        unit_price_internal: item.unit_price_internal ? Number(item.unit_price_internal) : null,
      }))
  } finally {
    pageLoading.value = false
  }
}

function buildPayload() {
  return {
    customer_id: form.customer_id,
    currency: form.currency,
    exchange_rate: form.exchange_rate || null,
    trade_terms: form.trade_terms || null,
    delivery_date: form.delivery_date || null,
    valid_until: form.valid_until || null,
    remarks: form.remarks || null,
    contact_person: form.contact_person || null,
    payment_terms: form.payment_terms || null,
    commodity: form.commodity || null,
    packing: form.packing || 'EXPORT STANDARD',
    port_of_loading: form.port_of_loading || null,
    destination_port: form.destination_port || null,
    note_pi: form.note_pi || null,
    items: form.items.map((item, idx) => ({
      product_id: item.product_id || null,
      grade_label: item.grade_label || null,
      hscode: item.hscode || null,
      description: item.description,
      quantity: item.quantity,
      unit: item.unit,
      unit_price: item.unit_price,
      unit_price_internal: item.unit_price_internal || null,
      sort_order: idx,
    })),
  }
}

async function handleCreate() {
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  if (form.items.length === 0) {
    message.warning('请至少添加一个产品')
    return
  }
  saving.value = true
  try {
    const res = await quotationsApi.create(buildPayload())
    message.success('报价单创建成功')
    router.replace(`/quotations/${res.data.id}`)
  } finally {
    saving.value = false
  }
}

async function handleSave() {
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  saving.value = true
  try {
    const res = await quotationsApi.update(quotationId.value, buildPayload())
    quotation.value = res.data
    message.success('保存成功')
  } finally {
    saving.value = false
  }
}

async function changeStatus(status) {
  try {
    const res = await quotationsApi.updateStatus(quotationId.value, status)
    quotation.value = res.data
    message.success('状态已更新')
  } catch (e) {
    message.error(e?.response?.data?.detail || '状态更新失败')
  }
}

async function downloadPI(isInternal) {
  try {
    const res = await api.get(
      `/quotations/${quotationId.value}/generate-pi`,
      { params: { internal: isInternal }, responseType: 'blob' }
    )
    const suffix = isInternal ? 'internal' : 'client'
    const filename = `${quotation.value?.pi_number}-${suffix}.pdf`
    const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  } catch {
    message.error('PDF 下载失败，请重试')
  }
}

async function handleConvert() {
  try {
    const res = await quotationsApi.convertToOrder(quotationId.value)
    message.success(`转单成功，订单号：${res.data.so_number}`)
    router.push(`/orders/${res.data.order_id}`)
  } catch (e) {
    message.error(e?.response?.data?.detail || '转单失败')
  }
}

onMounted(async () => {
  if (isNew.value) {
    await loadCustomers()
  } else {
    await Promise.all([loadCustomers(), loadQuotation()])
    // 将客户选项补入（防止客户不在当前分页内）
    if (quotation.value && !customerOptions.value.find((o) => o.value === form.customer_id)) {
      customerOptions.value.unshift({
        value: quotation.value.customer.id,
        label: `${quotation.value.customer.company_name} (${quotation.value.customer.country})`,
      })
    }
  }
})
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
</style>
