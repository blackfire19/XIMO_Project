<template>
  <div>
    <!-- 顶部 -->
    <div class="page-header">
      <a-space>
        <a-button @click="router.back()">返回</a-button>
        <a-typography-title :level="4" style="margin: 0">
          {{ isNew ? '新建核价单' : ps?.ps_number }}
        </a-typography-title>
        <a-tag v-if="!isNew" :color="statusColor(ps?.status)">{{ statusLabel(ps?.status) }}</a-tag>
      </a-space>

      <a-space v-if="!isNew">
        <template v-if="canEdit">
          <a-button :loading="saving" @click="handleSave">保存草稿</a-button>
          <a-popconfirm title="确认后可转生成PI，是否确认核价？" @confirm="handleConfirm">
            <a-button v-if="ps?.status === 'draft' && form.items.length > 0" type="primary">确认核价</a-button>
          </a-popconfirm>
        </template>
        <a-popconfirm
          v-if="ps?.status === 'confirmed'"
          title="转PI后核价单状态变为【已转PI】，确认？"
          @confirm="handleConvertToPI"
        >
          <a-button type="primary">转生成PI</a-button>
        </a-popconfirm>
        <template v-if="ps?.quotations?.length">
          <a-divider type="vertical" />
          <span style="color:#666; font-size:12px">已转PI：</span>
          <a-button
            v-for="q in ps.quotations"
            :key="q.id"
            type="link"
            size="small"
            style="padding:0 4px"
            @click="router.push(`/quotations/${q.id}`)"
          >
            {{ q.pi_number }}
            <a-tag :color="piStatusColor(q.status)" style="margin-left:2px; font-size:11px">{{ piStatusLabel(q.status) }}</a-tag>
          </a-button>
        </template>
      </a-space>

      <!-- 新建时的底部按钮区替换为顶部双按钮 -->
      <a-space v-if="isNew">
        <a-button :loading="saving" @click="handleCreate('draft')">保存草稿</a-button>
        <a-button v-if="form.items.length > 0" type="primary" :loading="saving" @click="handleCreate('confirmed')">确认核价</a-button>
      </a-space>
    </div>

    <a-spin :spinning="pageLoading">
      <!-- 表头参数 -->
      <a-card title="核价参数" size="small" style="margin-bottom: 16px">
        <a-form ref="formRef" :model="form" :rules="rules" layout="vertical" :disabled="!canEdit && !isNew">
          <a-row :gutter="16">
            <a-col :span="6">
              <a-form-item label="客户">
                <a-select
                  v-model:value="form.customer_id"
                  show-search
                  :filter-option="false"
                  placeholder="搜索客户（可选）"
                  :options="customerOptions"
                  allow-clear
                  @search="searchCustomers"
                />
              </a-form-item>
            </a-col>
            <a-col :span="4">
              <a-form-item label="贸易条款" name="trade_terms">
                <a-select v-model:value="form.trade_terms" allow-clear placeholder="请选择" @change="onTradeTermsChange">
                  <a-select-option v-for="t in TRADE_TERMS" :key="t" :value="t">{{ t }}</a-select-option>
                </a-select>
              </a-form-item>
            </a-col>
            <a-col :span="3">
              <a-form-item label="币种">
                <a-select v-model:value="form.currency">
                  <a-select-option value="USD">USD</a-select-option>
                  <a-select-option value="EUR">EUR</a-select-option>
                </a-select>
              </a-form-item>
            </a-col>
            <a-col :span="4">
              <a-form-item label="汇率（CNY → 外币）" name="exchange_rate">
                <a-input-number
                  v-model:value="form.exchange_rate"
                  :min="0.01" :precision="4"
                  style="width: 100%"
                  placeholder="如 7.2500"
                  @change="recalcAll"
                />
              </a-form-item>
            </a-col>
            <template v-if="isCIF">
              <a-col :span="4">
                <a-form-item label="海运费（USD/柜）">
                  <a-input-number
                    v-model:value="form.sea_freight"
                    :min="0" :precision="2"
                    style="width: 100%"
                    placeholder="如 2000"
                    @change="recalcAll"
                  />
                </a-form-item>
              </a-col>
              <a-col :span="3">
                <a-form-item label="单柜吨数（MT）">
                  <a-input-number
                    v-model:value="form.tons_per_container"
                    :min="0.001" :precision="3"
                    style="width: 100%"
                    placeholder="如 25"
                    @change="recalcAll"
                  />
                </a-form-item>
              </a-col>
            </template>
          </a-row>
          <a-row>
            <a-col :span="24">
              <a-form-item label="备注">
                <a-input v-model:value="form.remarks" placeholder="可选" />
              </a-form-item>
            </a-col>
          </a-row>
        </a-form>
      </a-card>

      <!-- 产品核价明细 -->
      <a-card size="small">
        <template #title>产品核价明细</template>
        <template #extra>
          <a-space v-if="canEdit || isNew">
            <a-button size="small" @click="openProductPicker">从产品库选择</a-button>
            <a-button size="small" @click="addCustomItem">手动添加</a-button>
          </a-space>
        </template>

        <a-table
          :columns="itemCols"
          :data-source="form.items"
          :pagination="false"
          row-key="__key"
          size="small"
          :scroll="{ x: 1400 }"
        >
          <template #bodyCell="{ column, record, index }">
            <!-- 牌号 -->
            <template v-if="column.key === 'grade_label'">
              <a-input v-if="canEdit||isNew" v-model:value="record.grade_label" size="small" placeholder="如Q235" style="width:70px" />
              <span v-else>{{ record.grade_label || '-' }}</span>
            </template>
            <!-- HS码 -->
            <template v-else-if="column.key === 'hscode'">
              <a-input v-if="canEdit||isNew" v-model:value="record.hscode" size="small" style="width:80px" />
              <span v-else>{{ record.hscode || '-' }}</span>
            </template>
            <!-- 描述 -->
            <template v-else-if="column.key === 'description'">
              <a-input v-if="canEdit||isNew" v-model:value="record.description" size="small" style="width:160px" />
              <span v-else>{{ record.description }}</span>
            </template>
            <!-- 数量 -->
            <template v-else-if="column.key === 'quantity'">
              <a-input-number v-if="canEdit||isNew" v-model:value="record.quantity" :min="0" :precision="3" size="small" style="width:75px" @change="recalcItem(record)" />
              <span v-else>{{ record.quantity }}</span>
            </template>
            <!-- 成本 -->
            <template v-else-if="column.key === 'cost'">
              <a-input-number v-if="canEdit||isNew" v-model:value="record.cost" :min="0" :precision="2" size="small" style="width:85px" @change="recalcItem(record)" />
              <span v-else>{{ record.cost }}</span>
            </template>
            <!-- 陆运 -->
            <template v-else-if="column.key === 'inland_freight'">
              <a-input-number v-if="canEdit||isNew" v-model:value="record.inland_freight" :min="0" :precision="2" size="small" style="width:75px" @change="recalcItem(record)" />
              <span v-else>{{ record.inland_freight }}</span>
            </template>
            <!-- 包装 -->
            <template v-else-if="column.key === 'packing_cost'">
              <a-input-number v-if="canEdit||isNew" v-model:value="record.packing_cost" :min="0" :precision="2" size="small" style="width:75px" @change="recalcItem(record)" />
              <span v-else>{{ record.packing_cost }}</span>
            </template>
            <!-- 港杂 -->
            <template v-else-if="column.key === 'port_charges'">
              <a-input-number v-if="canEdit||isNew" v-model:value="record.port_charges" :min="0" :precision="2" size="small" style="width:75px" @change="recalcItem(record)" />
              <span v-else>{{ record.port_charges }}</span>
            </template>
            <!-- 利润 -->
            <template v-else-if="column.key === 'profit'">
              <a-input-number v-if="canEdit||isNew" v-model:value="record.profit" :min="0" :precision="2" size="small" style="width:75px" @change="recalcItem(record)" />
              <span v-else>{{ record.profit }}</span>
            </template>
            <!-- 综合成本 -->
            <template v-else-if="column.key === 'total_cost'">
              <span class="muted">{{ totalCost(record) }}</span>
            </template>
            <!-- 计算报价 -->
            <template v-else-if="column.key === 'calculated_price'">
              <span class="price-result">{{ record.calculated_price ?? '-' }}</span>
            </template>
            <!-- 金额小计 -->
            <template v-else-if="column.key === 'amount'">
              <span>{{ lineAmount(record) }}</span>
            </template>
            <!-- 操作 -->
            <template v-else-if="column.key === 'actions'">
              <a-button v-if="canEdit||isNew" size="small" danger @click="removeItem(index)">删除</a-button>
            </template>
          </template>

          <template #summary>
            <a-table-summary-row>
              <a-table-summary-cell :col-span="4" align="right"><strong>合计</strong></a-table-summary-cell>
              <a-table-summary-cell align="center"><strong>{{ totalQty }}</strong></a-table-summary-cell>
              <a-table-summary-cell :col-span="6" />
              <a-table-summary-cell align="center">
                <strong>{{ totalAmount }} {{ form.currency }}</strong>
              </a-table-summary-cell>
              <a-table-summary-cell />
            </a-table-summary-row>
          </template>
        </a-table>

        <!-- 公式说明 -->
        <a-alert style="margin-top: 12px" type="info" show-icon>
          <template #message>
            <span v-if="!isCIF">
              报价 = (成本 + 陆运费 + 包装费 + 港杂 + 利润) ÷ 汇率
            </span>
            <span v-else>
              报价 = (成本 + 陆运费 + 包装费 + 港杂 + 利润) ÷ 汇率 + 海运费 ÷ 单柜吨数
            </span>
            &nbsp;｜&nbsp;单位：成本项 CNY/吨，报价 {{ form.currency }}/吨
          </template>
        </a-alert>
      </a-card>
    </a-spin>

    <!-- 说明附件 -->
    <a-card size="small" style="margin-top: 16px">
      <template #title>说明附件</template>
      <a-row :gutter="24">
        <!-- 陆运/包装费用说明 -->
        <a-col :span="12">
          <div class="attach-section">
            <div class="attach-label">
              <span>陆运/包装费用说明</span>
              <span class="attach-hint">（可选，仅供参考）</span>
            </div>
            <div class="image-grid">
              <div v-for="img in costImages" :key="img.id" class="image-item">
                <a :href="img.file_path" target="_blank">
                  <img :src="img.file_path" :alt="img.file_name" />
                </a>
                <div class="image-name">{{ img.file_name }}</div>
                <button class="del-btn" @click="deleteImage('cost_notes', img.id)">×</button>
              </div>
              <a-upload
                :show-upload-list="false"
                accept="image/*"
                :before-upload="(file) => handleUpload('cost_notes', file)"
              >
                <div class="upload-placeholder">
                  <plus-outlined />
                  <div>上传图片</div>
                </div>
              </a-upload>
            </div>
          </div>
        </a-col>

        <!-- 海运费说明 -->
        <a-col :span="12">
          <div class="attach-section">
            <div class="attach-label">
              <span>海运费说明</span>
              <span class="attach-hint">（可选，仅供参考）</span>
            </div>
            <div class="image-grid">
              <div v-for="img in freightImages" :key="img.id" class="image-item">
                <a :href="img.file_path" target="_blank">
                  <img :src="img.file_path" :alt="img.file_name" />
                </a>
                <div class="image-name">{{ img.file_name }}</div>
                <button class="del-btn" @click="deleteImage('freight_notes', img.id)">×</button>
              </div>
              <a-upload
                :show-upload-list="false"
                accept="image/*"
                :before-upload="(file) => handleUpload('freight_notes', file)"
              >
                <div class="upload-placeholder">
                  <plus-outlined />
                  <div>上传图片</div>
                </div>
              </a-upload>
            </div>
          </div>
        </a-col>
      </a-row>
    </a-card>

    <!-- 产品库选择弹窗 -->
    <a-modal v-model:open="pickerVisible" title="从产品库选择" width="780px" :footer="null">
      <a-input v-model:value="productSearch" placeholder="搜索规格/材质" style="margin-bottom:12px" allow-clear @input="filterProducts" />
      <a-table
        :columns="productCols"
        :data-source="filteredProducts"
        :loading="productsLoading"
        row-key="id"
        size="small"
        :pagination="{ pageSize: 10 }"
        :row-selection="{ selectedRowKeys: selectedIds, onChange: onSelect, type: 'checkbox' }"
      />
      <div style="margin-top:12px; text-align:right">
        <a-button type="primary" @click="confirmPick">添加选中（{{ selectedIds.length }}）</a-button>
      </div>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { PlusOutlined } from '@ant-design/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { pricingSheetsApi } from '@/api/pricingSheets'
import { customersApi } from '@/api/customers'
import { productsApi } from '@/api/products'

const TRADE_TERMS = ['EXW', 'FOB', 'CFR', 'CIF', 'DAP', 'DDP']

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const isNew = computed(() => route.params.id === 'new')
const psId = computed(() => isNew.value ? null : Number(route.params.id))

const ps = ref(null)
const pageLoading = ref(false)
const saving = ref(false)

// 图片附件
const costImages = ref([])
const freightImages = ref([])
function syncImages(data) {
  costImages.value = (data.images || []).filter(i => i.category === 'cost_notes')
  freightImages.value = (data.images || []).filter(i => i.category === 'freight_notes')
}
const formRef = ref()

const form = reactive({
  customer_id: undefined,
  trade_terms: undefined,
  currency: 'USD',
  exchange_rate: null,
  sea_freight: null,
  tons_per_container: null,
  remarks: '',
  items: [],
})

const rules = {
  exchange_rate: [{ required: true, message: '请填写汇率' }],
}

const isCIF = computed(() => form.trade_terms === 'CIF')

const canEdit = computed(() => {
  if (isNew.value) return true
  const role = auth.user?.role || ''
  if (role === 'super_admin') return true
  return role === 'salesperson' && ps.value?.salesperson?.id === auth.user?.id && ['draft', 'confirmed'].includes(ps.value?.status)
})

// 客户
const customerOptions = ref([])
const allCustomers = ref([])
async function loadCustomers() {
  const res = await customersApi.list({ page_size: 200 })
  const list = res.data.items ?? res.data
  allCustomers.value = list
  customerOptions.value = list.map(c => ({ value: c.id, label: `${c.company_name} (${c.country})` }))
}
function searchCustomers(val) {
  customerOptions.value = allCustomers.value
    .filter(c => c.company_name.toLowerCase().includes(val.toLowerCase()))
    .map(c => ({ value: c.id, label: `${c.company_name} (${c.country})` }))
}
function onTradeTermsChange() { recalcAll() }

// 行 key
let keyCounter = 0
const makeKey = () => ++keyCounter

// 核价公式
function calcPrice(item) {
  const rate = Number(form.exchange_rate) || 0
  if (!rate) return null
  const sum = (Number(item.cost) || 0)
    + (Number(item.inland_freight) || 0)
    + (Number(item.packing_cost) || 0)
    + (Number(item.port_charges) || 0)
    + (Number(item.profit) || 0)
  let price = sum / rate
  if (isCIF.value && form.sea_freight && form.tons_per_container) {
    price += Number(form.sea_freight) / Number(form.tons_per_container)
  }
  return Math.round(price * 10000) / 10000
}

function recalcItem(item) {
  item.calculated_price = calcPrice(item)
}

function recalcAll() {
  form.items.forEach(item => { item.calculated_price = calcPrice(item) })
}

function totalCost(item) {
  const s = (Number(item.cost) || 0)
    + (Number(item.inland_freight) || 0)
    + (Number(item.packing_cost) || 0)
    + (Number(item.port_charges) || 0)
    + (Number(item.profit) || 0)
  return s.toFixed(2)
}

function lineAmount(item) {
  if (!item.calculated_price || !item.quantity) return '-'
  return (Number(item.calculated_price) * Number(item.quantity)).toFixed(2)
}

const totalQty = computed(() =>
  form.items.reduce((s, i) => s + (Number(i.quantity) || 0), 0).toFixed(3)
)
const totalAmount = computed(() =>
  form.items.reduce((s, i) => s + (Number(i.calculated_price) || 0) * (Number(i.quantity) || 0), 0).toFixed(2)
)

// 表格列
const itemCols = [
  { title: '牌号', key: 'grade_label', width: 90 },
  { title: 'HS编码', key: 'hscode', width: 95 },
  { title: '产品描述', key: 'description', width: 170 },
  { title: '数量(MT)', key: 'quantity', width: 90 },
  { title: '成本(¥/T)', key: 'cost', width: 100 },
  { title: '陆运(¥/T)', key: 'inland_freight', width: 90 },
  { title: '包装(¥/T)', key: 'packing_cost', width: 90 },
  { title: '港杂(¥/T)', key: 'port_charges', width: 90 },
  { title: '利润(¥/T)', key: 'profit', width: 90 },
  { title: '综合成本(¥)', key: 'total_cost', width: 110 },
  { title: `报价(外币/T)`, key: 'calculated_price', width: 110 },
  { title: '金额小计', key: 'amount', width: 100 },
  { title: '操作', key: 'actions', width: 65, fixed: 'right' },
]

function addCustomItem() {
  form.items.push({
    __key: makeKey(),
    product_id: null,
    grade_label: '',
    hscode: '',
    description: '',
    quantity: 1,
    unit: 'MT',
    cost: 0,
    inland_freight: 0,
    packing_cost: 0,
    port_charges: 0,
    profit: 0,
    calculated_price: calcPrice({ cost: 0, inland_freight: 0, packing_cost: 0, port_charges: 0, profit: 0 }),
    sort_order: form.items.length,
  })
}

function removeItem(idx) { form.items.splice(idx, 1) }

// 产品库选择器
const pickerVisible = ref(false)
const productSearch = ref('')
const allProducts = ref([])
const filteredProducts = ref([])
const productsLoading = ref(false)
const selectedIds = ref([])
const selectedRows = ref([])

const productCols = [
  { title: '规格', dataIndex: 'spec', key: 'spec' },
  { title: '材质', dataIndex: 'material', key: 'material', width: 80 },
  { title: '长度', dataIndex: 'length', key: 'length', width: 90 },
  { title: '成本单价(¥/T)', dataIndex: 'unit_price', key: 'unit_price', width: 120 },
  { title: '仓库', dataIndex: 'warehouse', key: 'warehouse', width: 90 },
]

async function openProductPicker() {
  pickerVisible.value = true
  selectedIds.value = []
  selectedRows.value = []
  productSearch.value = ''
  if (!allProducts.value.length) {
    productsLoading.value = true
    try { allProducts.value = (await productsApi.list()).data }
    finally { productsLoading.value = false }
  }
  filteredProducts.value = allProducts.value
}
function filterProducts() {
  const kw = productSearch.value.toLowerCase()
  filteredProducts.value = kw
    ? allProducts.value.filter(p => p.spec.toLowerCase().includes(kw) || (p.material || '').toLowerCase().includes(kw))
    : allProducts.value
}
function onSelect(keys, rows) { selectedIds.value = keys; selectedRows.value = rows }

function confirmPick() {
  const base = form.items.length
  selectedRows.value.forEach((p, i) => {
    const newItem = {
      __key: makeKey(),
      product_id: p.id,
      grade_label: p.material || '',
      hscode: '',
      description: `${p.spec}${p.length ? ' L=' + p.length : ''}`.trim(),
      quantity: 1,
      unit: 'MT',
      cost: p.unit_price ? Number(p.unit_price) : 0,
      inland_freight: 0,
      packing_cost: 0,
      port_charges: 0,
      profit: 0,
      sort_order: base + i,
    }
    newItem.calculated_price = calcPrice(newItem)
    form.items.push(newItem)
  })
  pickerVisible.value = false
}

// 状态
function statusColor(s) { return { draft: 'default', confirmed: 'blue', converted: 'green' }[s] || 'default' }
function statusLabel(s) { return { draft: '草稿', confirmed: '已确认', converted: '已转PI' }[s] || s }
function piStatusColor(s) { return { draft: 'default', sent: 'blue', won: 'green', expired: 'red' }[s] || 'default' }
function piStatusLabel(s) { return { draft: '草稿', sent: '已发送', won: '已成交', expired: '已作废' }[s] || s }

// 加载
async function loadPS() {
  pageLoading.value = true
  try {
    const res = await pricingSheetsApi.get(psId.value)
    ps.value = res.data
    const d = res.data
    form.customer_id = d.customer?.id || undefined
    form.trade_terms = d.trade_terms || undefined
    form.currency = d.currency
    form.exchange_rate = d.exchange_rate ? Number(d.exchange_rate) : null
    form.sea_freight = d.sea_freight ? Number(d.sea_freight) : null
    form.tons_per_container = d.tons_per_container ? Number(d.tons_per_container) : null
    form.remarks = d.remarks || ''
    form.items = (d.items || [])
      .sort((a, b) => a.sort_order - b.sort_order)
      .map(i => ({
        ...i,
        __key: makeKey(),
        cost: Number(i.cost),
        inland_freight: Number(i.inland_freight),
        packing_cost: Number(i.packing_cost),
        port_charges: Number(i.port_charges),
        profit: Number(i.profit),
        quantity: Number(i.quantity),
        calculated_price: i.calculated_price ? Number(i.calculated_price) : null,
      }))
    syncImages(d)
  } finally {
    pageLoading.value = false
  }
}

async function handleUpload(category, file) {
  try {
    let id = psId.value
    // 新建状态先自动保存草稿获取 ID
    if (isNew.value) {
      if (!form.exchange_rate) { message.warning('请先填写汇率后再上传图片'); return false }
      saving.value = true
      try {
        const created = await pricingSheetsApi.create(buildPayload())
        id = created.data.id
        await router.replace(`/pricing-sheets/${id}`)
        ps.value = created.data
        syncImages(created.data)
      } finally { saving.value = false }
    }
    const res = await pricingSheetsApi.uploadImage(id, category, file)
    const newImg = res.data
    if (category === 'cost_notes') costImages.value.push(newImg)
    else freightImages.value.push(newImg)
    message.success('上传成功')
  } catch (e) {
    message.error('上传失败，请重试')
  }
  return false
}

async function deleteImage(category, imageId) {
  try {
    await pricingSheetsApi.deleteImage(psId.value, imageId)
    if (category === 'cost_notes') {
      costImages.value = costImages.value.filter(i => i.id !== imageId)
    } else {
      freightImages.value = freightImages.value.filter(i => i.id !== imageId)
    }
    message.success('已删除')
  } catch (e) {
    message.error('删除失败，请重试')
  }
}

function buildPayload() {
  return {
    customer_id: form.customer_id || null,
    trade_terms: form.trade_terms || null,
    currency: form.currency,
    exchange_rate: form.exchange_rate,
    sea_freight: isCIF.value ? (form.sea_freight || null) : null,
    tons_per_container: isCIF.value ? (form.tons_per_container || null) : null,
    remarks: form.remarks || null,
    items: form.items.map((item, idx) => ({
      product_id: item.product_id || null,
      grade_label: item.grade_label || null,
      hscode: item.hscode || null,
      description: item.description || '-',
      quantity: item.quantity,
      unit: item.unit,
      cost: item.cost || 0,
      inland_freight: item.inland_freight || 0,
      packing_cost: item.packing_cost || 0,
      port_charges: item.port_charges || 0,
      profit: item.profit || 0,
      sort_order: idx,
    })),
  }
}

async function handleCreate(targetStatus = 'draft') {
  try { await formRef.value.validate() } catch { return }
  if (!form.items.length) { message.warning('请至少添加一条产品'); return }
  saving.value = true
  try {
    const res = await pricingSheetsApi.create(buildPayload())
    // 如果直接确认，创建后立即调用确认接口
    if (targetStatus === 'confirmed') {
      await pricingSheetsApi.confirm(res.data.id)
      message.success('核价单已确认，可转生成PI')
    } else {
      message.success('草稿已保存')
    }
    router.replace(`/pricing-sheets/${res.data.id}`)
  } finally { saving.value = false }
}

async function handleSave() {
  try { await formRef.value.validate() } catch { return }
  saving.value = true
  try {
    const res = await pricingSheetsApi.update(psId.value, buildPayload())
    ps.value = res.data
    syncImages(res.data)
    message.success('保存成功')
  } finally { saving.value = false }
}

async function handleConfirm() {
  try {
    const res = await pricingSheetsApi.confirm(psId.value)
    ps.value = res.data
    message.success('核价单已确认')
  } catch (e) {
    message.error(e?.response?.data?.detail || '确认失败')
  }
}

async function handleConvertToPI() {
  try {
    const res = await pricingSheetsApi.convertToPI(psId.value)
    message.success(`已生成 PI：${res.data.pi_number}`)
    router.push(`/quotations/${res.data.quotation_id}`)
  } catch (e) {
    message.error(e?.response?.data?.detail || '转PI失败')
  }
}

onMounted(async () => {
  await loadCustomers()
  if (!isNew.value) {
    await loadPS()
    if (ps.value?.customer && !customerOptions.value.find(o => o.value === form.customer_id)) {
      customerOptions.value.unshift({
        value: ps.value.customer.id,
        label: `${ps.value.customer.company_name} (${ps.value.customer.country})`,
      })
    }
  }
})
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.price-result { font-weight: bold; color: #1a5276; font-size: 13px; }
.muted { color: #666; }

.attach-section { margin-bottom: 16px; }
.attach-label { font-weight: 500; margin-bottom: 8px; color: #333; }
.attach-hint { font-size: 12px; color: #999; margin-left: 8px; }
.image-grid { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 8px; }
.image-item { position: relative; width: 100px; text-align: center; }
.image-item img { width: 100px; height: 80px; object-fit: cover; border: 1px solid #e0e0e0; border-radius: 4px; cursor: pointer; }
.image-name { font-size: 11px; color: #666; margin-top: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.del-btn { position: absolute; top: -6px; right: -6px; background: rgba(0,0,0,0.5); color: #fff; border: none; border-radius: 50%; width: 18px; height: 18px; font-size: 11px; cursor: pointer; display: flex; align-items: center; justify-content: center; padding: 0; }
.del-btn:hover { background: #f00; }
.upload-placeholder { display: flex; flex-direction: column; align-items: center; justify-content: center; width: 100px; height: 80px; border: 1px dashed #bbb; border-radius: 4px; cursor: pointer; color: #999; font-size: 12px; transition: border-color 0.2s; }
.upload-placeholder:hover { border-color: #1677ff; color: #1677ff; }
.upload-placeholder.disabled { cursor: not-allowed; opacity: 0.5; }
</style>
