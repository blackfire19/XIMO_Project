<template>
  <div v-if="order">
    <!-- 页头 -->
    <div class="page-header">
      <div>
        <a-button @click="router.back()" style="margin-right: 8px">← 返回</a-button>
        <a-typography-title :level="4" style="margin: 0; display: inline">
          {{ order.so_number }}
        </a-typography-title>
        <a-tag :color="statusColor(order.status)" style="margin-left: 12px; font-size: 14px">
          {{ statusLabel(order.status) }}
        </a-tag>
        <a-tag v-if="order.quotation_id" color="blue" style="cursor:pointer; margin-left: 4px"
          @click="router.push(`/quotations/${order.quotation_id}`)">
          查看 PI
        </a-tag>
      </div>
      <a-space v-if="canEdit">
        <a-button
          v-for="next in nextStatuses"
          :key="next.value"
          type="primary"
          :loading="statusLoading"
          @click="openStatusModal(next)"
        >
          {{ next.action }}
        </a-button>
      </a-space>
    </div>

    <a-row :gutter="16">
      <!-- 左栏：基本信息 + 产品明细 -->
      <a-col :span="14">
        <a-card title="基本信息" size="small" style="margin-bottom: 16px">
          <a-descriptions :column="2" size="small">
            <a-descriptions-item label="客户">{{ order.customer.company_name }}</a-descriptions-item>
            <a-descriptions-item label="业务员">{{ order.salesperson.full_name }}</a-descriptions-item>
            <a-descriptions-item label="币种">{{ order.currency }}</a-descriptions-item>
            <a-descriptions-item label="汇率">{{ order.exchange_rate || '-' }}</a-descriptions-item>
            <a-descriptions-item label="贸易条款">{{ order.trade_terms || '-' }}</a-descriptions-item>
            <a-descriptions-item label="预计备货完成">
              <span v-if="order.est_ready_date">
                {{ order.est_ready_date }}
                <a-tag v-if="order.status === 'production'" color="orange" style="margin-left: 4px">
                  {{ countdownDays(order.est_ready_date) }}
                </a-tag>
              </span>
              <span v-else>-</span>
            </a-descriptions-item>
            <a-descriptions-item label="备注" :span="2">{{ order.remarks || '-' }}</a-descriptions-item>
            <a-descriptions-item label="创建时间">{{ order.created_at }}</a-descriptions-item>
          </a-descriptions>
        </a-card>

        <a-card title="产品明细" size="small" style="margin-bottom: 16px">
          <a-table
            :columns="itemColumns"
            :data-source="order.items"
            row-key="id"
            :pagination="false"
            size="small"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'total'">
                {{ (record.quantity * record.unit_price).toFixed(2) }}
              </template>
            </template>
            <template #summary>
              <a-table-summary-row>
                <a-table-summary-cell :index="0" :col-span="3">合计</a-table-summary-cell>
                <a-table-summary-cell :index="3">
                  {{ totalQty.toFixed(3) }} MT
                </a-table-summary-cell>
                <a-table-summary-cell :index="4" />
                <a-table-summary-cell :index="5">
                  {{ order.currency }} {{ totalAmount.toFixed(2) }}
                </a-table-summary-cell>
              </a-table-summary-row>
            </template>
          </a-table>
        </a-card>
      </a-col>

      <!-- 右栏：出运信息 + 附件 -->
      <a-col :span="10">
        <!-- 出运信息 -->
        <a-card size="small" style="margin-bottom: 16px">
          <template #title>
            <span>出运信息</span>
          </template>
          <template #extra>
            <a-button
              v-if="canEdit"
              type="link"
              size="small"
              @click="openShipmentModal(null)"
            >
              + 添加
            </a-button>
          </template>

          <a-empty v-if="!order.shipments.length" description="暂无出运记录" :image-size="40" />

          <a-collapse v-else ghost>
            <a-collapse-panel
              v-for="s in order.shipments"
              :key="s.id"
              :header="`${shipTypeLabel(s.ship_type)} — ${s.vessel_voyage || '待填写'}`"
            >
              <template #extra>
                <a-tag :color="shipStatusColor(s.status)">{{ shipStatusLabel(s.status) }}</a-tag>
                <a-space v-if="canEdit" style="margin-left: 8px" @click.stop>
                  <a-button size="small" @click="openShipmentModal(s)">编辑</a-button>
                  <a-popconfirm title="确认删除？" @confirm="deleteShipment(s.id)">
                    <a-button size="small" danger>删除</a-button>
                  </a-popconfirm>
                </a-space>
              </template>
              <a-descriptions size="small" :column="1">
                <template v-if="s.ship_type === 'container'">
                  <a-descriptions-item label="箱型">{{ s.container_type || '-' }}</a-descriptions-item>
                  <a-descriptions-item label="箱号">{{ s.container_number || '-' }}</a-descriptions-item>
                  <a-descriptions-item label="封号">{{ s.seal_number || '-' }}</a-descriptions-item>
                </template>
                <template v-else>
                  <a-descriptions-item label="重量(MT)">{{ s.weight_mt || '-' }}</a-descriptions-item>
                </template>
                <a-descriptions-item label="船名航次">{{ s.vessel_voyage || '-' }}</a-descriptions-item>
                <a-descriptions-item label="ETD">{{ s.etd || '-' }}</a-descriptions-item>
                <a-descriptions-item label="ETA">{{ s.eta || '-' }}</a-descriptions-item>
                <a-descriptions-item label="提单号">{{ s.bl_number || '-' }}</a-descriptions-item>
                <a-descriptions-item v-if="s.remarks" label="备注">{{ s.remarks }}</a-descriptions-item>
              </a-descriptions>
              <a-space v-if="canEdit && nextShipStatuses(s.status).length" style="margin-top: 8px">
                <a-button
                  v-for="ns in nextShipStatuses(s.status)"
                  :key="ns.value"
                  size="small"
                  type="primary"
                  ghost
                  @click="advanceShipStatus(s, ns.value)"
                >
                  {{ ns.label }}
                </a-button>
              </a-space>
            </a-collapse-panel>
          </a-collapse>
        </a-card>

        <!-- 单据附件 -->
        <a-card size="small">
          <template #title>单据归档</template>
          <template #extra>
            <a-button v-if="canEdit" type="link" size="small" @click="uploadVisible = true">
              + 上传
            </a-button>
          </template>

          <a-empty v-if="!order.attachments.length" description="暂无附件" :image-size="40" />

          <a-list v-else size="small" :data-source="order.attachments">
            <template #renderItem="{ item }">
              <a-list-item>
                <a-list-item-meta>
                  <template #title>
                    <a :href="`/uploads/${item.file_path}`" target="_blank">{{ item.file_name }}</a>
                  </template>
                  <template #description>
                    <a-tag>{{ docTypeLabel(item.doc_type) }}</a-tag>
                    {{ item.uploaded_at }}
                  </template>
                </a-list-item-meta>
                <template #actions v-if="canEdit">
                  <a-popconfirm title="确认删除？" @confirm="deleteAttachment(item.id)">
                    <a-button type="link" danger size="small">删除</a-button>
                  </a-popconfirm>
                </template>
              </a-list-item>
            </template>
          </a-list>
        </a-card>
      </a-col>
    </a-row>

    <!-- 状态变更弹窗 -->
    <a-modal
      v-model:open="statusModal.visible"
      :title="`确认：${statusModal.action}`"
      @ok="confirmStatusChange"
      :confirm-loading="statusLoading"
    >
      <a-form v-if="statusModal.next === 'production'" layout="vertical">
        <a-form-item label="预计备货完成日期">
          <a-date-picker v-model:value="statusModal.estReadyDate" style="width: 100%" value-format="YYYY-MM-DD" />
        </a-form-item>
      </a-form>
      <p v-else>确认将订单状态改为「{{ statusModal.nextLabel }}」？</p>
    </a-modal>

    <!-- 出运记录弹窗 -->
    <a-modal
      v-model:open="shipModal.visible"
      :title="shipModal.id ? '编辑出运记录' : '添加出运记录'"
      width="600px"
      @ok="saveShipment"
      :confirm-loading="shipModal.loading"
    >
      <a-form :model="shipModal.form" layout="vertical">
        <a-form-item label="类型">
          <a-radio-group v-model:value="shipModal.form.ship_type">
            <a-radio value="container">集装箱</a-radio>
            <a-radio value="bulk">散货船</a-radio>
          </a-radio-group>
        </a-form-item>
        <template v-if="shipModal.form.ship_type === 'container'">
          <a-row :gutter="12">
            <a-col :span="8">
              <a-form-item label="箱型">
                <a-select v-model:value="shipModal.form.container_type" allow-clear placeholder="20GP/40HC...">
                  <a-select-option value="20GP">20GP</a-select-option>
                  <a-select-option value="40GP">40GP</a-select-option>
                  <a-select-option value="40HC">40HC</a-select-option>
                  <a-select-option value="45HC">45HC</a-select-option>
                </a-select>
              </a-form-item>
            </a-col>
            <a-col :span="8">
              <a-form-item label="箱号">
                <a-input v-model:value="shipModal.form.container_number" />
              </a-form-item>
            </a-col>
            <a-col :span="8">
              <a-form-item label="封号">
                <a-input v-model:value="shipModal.form.seal_number" />
              </a-form-item>
            </a-col>
          </a-row>
        </template>
        <template v-else>
          <a-form-item label="重量 (MT)">
            <a-input-number v-model:value="shipModal.form.weight_mt" style="width: 100%" :min="0" />
          </a-form-item>
        </template>
        <a-row :gutter="12">
          <a-col :span="12">
            <a-form-item label="船名航次">
              <a-input v-model:value="shipModal.form.vessel_voyage" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="提单号">
              <a-input v-model:value="shipModal.form.bl_number" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-row :gutter="12">
          <a-col :span="12">
            <a-form-item label="ETD">
              <a-date-picker v-model:value="shipModal.form.etd" style="width: 100%" value-format="YYYY-MM-DD" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="ETA">
              <a-date-picker v-model:value="shipModal.form.eta" style="width: 100%" value-format="YYYY-MM-DD" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="备注">
          <a-textarea v-model:value="shipModal.form.remarks" :rows="2" />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 上传附件弹窗 -->
    <a-modal
      v-model:open="uploadVisible"
      title="上传单据附件"
      @ok="doUpload"
      @cancel="uploadVisible = false"
      :confirm-loading="uploadLoading"
      @after-close="() => { if (fileInput) fileInput.value = null }"
    >
      <a-form layout="vertical">
        <a-form-item label="文件类型" required>
          <a-select v-model:value="uploadForm.doc_type" style="width: 100%">
            <a-select-option v-for="d in DOC_TYPES" :key="d.value" :value="d.value">{{ d.label }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="文件" required>
          <input type="file" ref="fileInput" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>

  <a-spin v-else style="display: block; margin: 60px auto" />
</template>

<script setup>
import { ref, computed, onMounted, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { useAuthStore } from '@/stores/auth'
import { orderApi } from '@/api/orders'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const order = ref(null)
const statusLoading = ref(false)

const STATUS_TRANSITIONS = {
  confirmed: [{ value: 'production', action: '开始生产备货', label: '生产备货中' }],
  production: [{ value: 'ready', action: '标记备货完成', label: '待出运' }],
  ready: [{ value: 'shipped', action: '标记已出运', label: '已出运' }],
  shipped: [{ value: 'completed', action: '完结订单', label: '已完结' }],
  completed: [],
}

const SHIP_STATUS_NEXT = {
  planned: [{ value: 'loaded', label: '已装船' }],
  loaded: [{ value: 'transit', label: '在途' }],
  transit: [{ value: 'arrived', label: '已到港' }],
  arrived: [],
}

const DOC_TYPES = [
  { value: 'MTC', label: 'MTC 材质证书' },
  { value: 'CO', label: 'CO 原产地证书' },
  { value: 'export_permit', label: '出口许可证' },
  { value: 'customs', label: '报关单据' },
  { value: 'other', label: '其他' },
]

const canEdit = computed(() => {
  if (!order.value) return false
  const role = auth.user?.role
  if (role === 'super_admin') return true
  if (role === 'salesperson') return order.value.salesperson?.id === auth.user?.id
  return false
})

const nextStatuses = computed(() => {
  if (!order.value) return []
  return STATUS_TRANSITIONS[order.value.status] || []
})

const totalQty = computed(() => (order.value?.items || []).reduce((s, i) => s + Number(i.quantity), 0))
const totalAmount = computed(() => (order.value?.items || []).reduce((s, i) => s + Number(i.quantity) * Number(i.unit_price), 0))

const itemColumns = [
  { title: '#', dataIndex: 'sort_order', key: 'sort_order', width: 50 },
  { title: '描述', dataIndex: 'description', key: 'description' },
  { title: '单位', dataIndex: 'unit', key: 'unit', width: 70 },
  { title: '数量', dataIndex: 'quantity', key: 'quantity', width: 90 },
  { title: '单价', dataIndex: 'unit_price', key: 'unit_price', width: 90 },
  { title: '金额', key: 'total', width: 100 },
]

// 状态弹窗
const statusModal = reactive({ visible: false, next: '', nextLabel: '', action: '', estReadyDate: null })

function openStatusModal(next) {
  statusModal.next = next.value
  statusModal.nextLabel = next.label
  statusModal.action = next.action
  statusModal.estReadyDate = null
  statusModal.visible = true
}

async function confirmStatusChange() {
  statusLoading.value = true
  try {
    const body = { status: statusModal.next }
    if (statusModal.next === 'production' && statusModal.estReadyDate) {
      body.est_ready_date = statusModal.estReadyDate
    }
    await orderApi.updateStatus(order.value.id, body)
    statusModal.visible = false
    await loadOrder()
    message.success('状态已更新')
  } catch (e) {
    message.error(e.response?.data?.detail || '操作失败')
  } finally {
    statusLoading.value = false
  }
}

// 出运弹窗
const shipModal = reactive({
  visible: false, id: null, loading: false,
  form: { ship_type: 'container', container_type: null, container_number: '', seal_number: '', vessel_voyage: '', bl_number: '', etd: null, eta: null, weight_mt: null, remarks: '' },
})

function openShipmentModal(shipment) {
  if (shipment) {
    Object.assign(shipModal.form, { ...shipment })
    shipModal.id = shipment.id
  } else {
    Object.assign(shipModal.form, { ship_type: 'container', container_type: null, container_number: '', seal_number: '', vessel_voyage: '', bl_number: '', etd: null, eta: null, weight_mt: null, remarks: '' })
    shipModal.id = null
  }
  shipModal.visible = true
}

async function saveShipment() {
  shipModal.loading = true
  try {
    if (shipModal.id) {
      await orderApi.updateShipment(order.value.id, shipModal.id, shipModal.form)
    } else {
      await orderApi.addShipment(order.value.id, shipModal.form)
    }
    shipModal.visible = false
    await loadOrder()
    message.success('保存成功')
  } catch (e) {
    message.error(e.response?.data?.detail || '保存失败')
  } finally {
    shipModal.loading = false
  }
}

async function deleteShipment(shipmentId) {
  try {
    await orderApi.deleteShipment(order.value.id, shipmentId)
    await loadOrder()
    message.success('已删除')
  } catch (e) {
    message.error(e.response?.data?.detail || '删除失败')
  }
}

async function advanceShipStatus(shipment, newStatus) {
  try {
    await orderApi.updateShipment(order.value.id, shipment.id, { ...shipment, status: newStatus })
    await loadOrder()
    message.success('出运状态已更新')
  } catch (e) {
    message.error(e.response?.data?.detail || '操作失败')
  }
}

// 附件
const uploadVisible = ref(false)
const uploadLoading = ref(false)
const fileInput = ref(null)
const uploadForm = reactive({ doc_type: 'MTC' })

async function doUpload() {
  const file = fileInput.value?.files?.[0]
  if (!file) { message.warning('请选择文件'); return }
  if (!uploadForm.doc_type) { message.warning('请选择文件类型'); return }

  uploadLoading.value = true
  try {
    const fd = new FormData()
    fd.append('doc_type', uploadForm.doc_type)
    fd.append('file', file)
    await orderApi.uploadAttachment(order.value.id, fd)
    uploadVisible.value = false
    await loadOrder()
    message.success('上传成功')
  } catch (e) {
    message.error(e.response?.data?.detail || '上传失败')
  } finally {
    uploadLoading.value = false
  }
}

async function deleteAttachment(attId) {
  try {
    await orderApi.deleteAttachment(order.value.id, attId)
    await loadOrder()
    message.success('已删除')
  } catch (e) {
    message.error(e.response?.data?.detail || '删除失败')
  }
}

// 辅助函数
const STATUS_COLOR = { confirmed: 'blue', production: 'orange', ready: 'cyan', shipped: 'purple', completed: 'green' }
const STATUS_LABEL = { confirmed: '已确认', production: '生产备货中', ready: '待出运', shipped: '已出运', completed: '已完结' }
function statusColor(s) { return STATUS_COLOR[s] || 'default' }
function statusLabel(s) { return STATUS_LABEL[s] || s }

const SHIP_STATUS_COLOR = { planned: 'default', loaded: 'blue', transit: 'orange', arrived: 'green' }
const SHIP_STATUS_LABEL = { planned: '计划中', loaded: '已装船', transit: '在途', arrived: '已到港' }
function shipStatusColor(s) { return SHIP_STATUS_COLOR[s] || 'default' }
function shipStatusLabel(s) { return SHIP_STATUS_LABEL[s] || s }
function shipTypeLabel(t) { return t === 'container' ? '集装箱' : '散货船' }
function nextShipStatuses(s) { return SHIP_STATUS_NEXT[s] || [] }

function docTypeLabel(t) { return DOC_TYPES.find(d => d.value === t)?.label || t }

function countdownDays(dateStr) {
  const diff = Math.ceil((new Date(dateStr) - new Date()) / 86400000)
  if (diff < 0) return `逾期 ${-diff} 天`
  if (diff === 0) return '今天完成'
  return `还有 ${diff} 天`
}

async function loadOrder() {
  const res = await orderApi.get(route.params.id)
  order.value = res.data
}

onMounted(loadOrder)
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
</style>
