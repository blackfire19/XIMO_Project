<template>
  <div v-if="order">
    <a-page-header :title="order.so_number" @back="$router.back()">
      <template #tags>
        <a-tag :color="STATUS_COLOR[order.status]">{{ STATUS_LABEL[order.status] }}</a-tag>
        <a-tag :color="order.is_stock ? 'blue' : 'gold'">{{ order.is_stock ? '现货' : '非现货' }}</a-tag>
      </template>
      <template #extra>
        <a-popconfirm
          v-if="canEdit && nextStatus"
          :title="advanceTitle"
          @confirm="advance"
        >
          <a-button type="primary">推进到「{{ STATUS_LABEL[nextStatus] }}」</a-button>
        </a-popconfirm>
      </template>
      <a-descriptions size="small" :column="3">
        <a-descriptions-item label="客户">{{ order.customer.company_name }}</a-descriptions-item>
        <a-descriptions-item label="业务员">{{ order.salesperson.full_name }}</a-descriptions-item>
        <a-descriptions-item label="创建时间">{{ (order.created_at || '').slice(0,10) }}</a-descriptions-item>
        <a-descriptions-item v-if="!order.is_stock" label="预计生产完成">
          {{ order.est_production_date || '未设置' }}
        </a-descriptions-item>
        <a-descriptions-item label="备注">{{ order.remarks || '—' }}</a-descriptions-item>
      </a-descriptions>
    </a-page-header>

    <!-- 生产倒计时 -->
    <a-alert
      v-if="!order.is_stock && countdown !== null && order.status !== 'completed'"
      :type="countdown < 0 ? 'error' : (countdown <= 7 ? 'warning' : 'info')"
      show-icon
      style="margin:16px 0"
      :message="countdown < 0
        ? `生产已超期 ${-countdown} 天，请尽快跟进`
        : `距预计生产完成还有 ${countdown} 天`"
    />

    <!-- 提单信息（一个订单一张提单） -->
    <a-card size="small" title="提单信息" style="margin-bottom:16px">
      <template #extra>
        <a-space v-if="canEdit">
          <a-button v-if="!bl" type="primary" size="small" @click="openBL(false)">创建提单</a-button>
          <template v-else>
            <a-button size="small" @click="openBL(true)">编辑</a-button>
            <a-popconfirm title="删除提单将同时删除其下集装箱，确认？" @confirm="delBL">
              <a-button size="small" danger>删除</a-button>
            </a-popconfirm>
          </template>
        </a-space>
      </template>

      <a-empty v-if="!bl" :image="emptyImage" description="暂无提单信息" />
      <a-descriptions v-else size="small" :column="3" bordered>
        <a-descriptions-item label="运输方式">
          <a-tag :color="bl.ship_type === 'bulk' ? 'purple' : 'blue'">
            {{ bl.ship_type === 'bulk' ? '散货船' : '集装箱' }}
          </a-tag>
        </a-descriptions-item>
        <a-descriptions-item label="提单号">{{ bl.bl_number || '—' }}</a-descriptions-item>
        <a-descriptions-item v-if="bl.ship_type === 'container'" label="箱型箱量">{{ bl.container_info || '—' }}</a-descriptions-item>
        <a-descriptions-item label="状态">
          <a-select
            v-if="canEdit"
            :value="bl.status"
            size="small"
            style="width:120px"
            @change="(v) => changeBLStatus(v)"
          >
            <a-select-option v-for="(l, k) in BL_STATUS_LABEL" :key="k" :value="k">{{ l }}</a-select-option>
          </a-select>
          <span v-else>{{ BL_STATUS_LABEL[bl.status] }}</span>
        </a-descriptions-item>
        <a-descriptions-item label="船名航次">{{ bl.vessel_voyage || '—' }}</a-descriptions-item>
        <a-descriptions-item label="起运港">{{ bl.load_port || '—' }}</a-descriptions-item>
        <a-descriptions-item label="目的港">{{ bl.discharge_port || '—' }}</a-descriptions-item>
        <a-descriptions-item label="ETD">{{ bl.etd || '—' }}</a-descriptions-item>
        <a-descriptions-item label="ETA">{{ bl.eta || '—' }}</a-descriptions-item>
        <a-descriptions-item label="备注">{{ bl.remarks || '—' }}</a-descriptions-item>
        <template v-if="bl.ship_type === 'bulk'">
          <a-descriptions-item label="件数">{{ bl.pieces ?? '—' }}</a-descriptions-item>
          <a-descriptions-item label="重量(MT)">{{ bl.weight_mt ?? '—' }}</a-descriptions-item>
          <a-descriptions-item label="体积(CBM)">{{ bl.volume_cbm ?? '—' }}</a-descriptions-item>
        </template>
      </a-descriptions>
    </a-card>

    <!-- 节点提醒（紧贴文件归档，提示该节点需准备的文件） -->
    <a-alert :type="reminder.type" show-icon style="margin:16px 0" :message="reminder.title">
      <template #description>
        <ul style="margin:4px 0 0; padding-left:18px">
          <li v-for="(item, i) in reminder.items" :key="i" :style="{ color: item.done ? '#52c41a' : '#fa541c' }">
            {{ item.done ? '✓' : '○' }} {{ item.text }}
          </li>
        </ul>
      </template>
    </a-alert>

    <!-- 来自询价单的文件（核价单 / PI 最新版本，只读） -->
    <a-card size="small" title="询价单文件（核价单 / PI 最新版本）" style="margin-bottom:16px">
      <template #extra>
        <a-button type="link" size="small"
          @click="$router.push({ name: 'InquiryDetail', params: { id: order.inquiry_id } })">
          查看询价单 →
        </a-button>
      </template>
      <a-empty v-if="!order.inquiry_files || order.inquiry_files.length === 0"
        :image="emptyImage" description="询价单暂无核价单 / PI" />
      <a-list v-else size="small" :data-source="order.inquiry_files">
        <template #renderItem="{ item }">
          <a-list-item>
            <a-list-item-meta>
              <template #title>
                <a-tag :color="item.doc_type === 'pricing_sheet' ? 'blue' : 'purple'">
                  {{ item.doc_type === 'pricing_sheet' ? '核价单' : 'PI' }}
                </a-tag>
                <a :href="`/uploads/${item.file_path}`" target="_blank">{{ item.file_name }}</a>
                <a-tag color="green" style="margin-left:8px">v{{ item.version }}</a-tag>
              </template>
              <template #description>{{ (item.uploaded_at || '').slice(0,10) }}</template>
            </a-list-item-meta>
          </a-list-item>
        </template>
      </a-list>
    </a-card>

    <!-- 文件归档 -->
    <a-card size="small" title="文件归档" :bordered="false" :body-style="{ padding: 0 }">
      <a-alert
        v-if="locked"
        type="info"
        show-icon
        banner
        message="订单已进入出运阶段，以下归档文件已锁定，仅可查看。如需补充，请使用下方「补充附件」。"
        style="margin-bottom:12px"
      />
      <a-row :gutter="16">
        <a-col v-for="dt in DOC_DEFS" :key="dt.key" :span="6">
          <a-card size="small" :title="dt.label" style="margin-bottom:16px">
            <template #extra>
              <a-upload
                v-if="canEdit && !locked"
                :before-upload="(f) => beforeUpload(f, dt.key)"
                :show-upload-list="false"
              >
                <a-button type="link" size="small">上传</a-button>
              </a-upload>
            </template>
            <a-empty v-if="!filesByType[dt.key] || filesByType[dt.key].length === 0"
              :image="emptyImage" description="暂无" />
            <a-list v-else size="small" :data-source="filesByType[dt.key]">
              <template #renderItem="{ item }">
                <a-list-item>
                  <a :href="`/uploads/${item.file_path}`" target="_blank">{{ item.file_name }}</a>
                  <template #actions>
                    <a-popconfirm v-if="canEdit && !locked" title="删除？" @confirm="delFile(item.id)">
                      <a style="color:#ff4d4f">删除</a>
                    </a-popconfirm>
                  </template>
                </a-list-item>
              </template>
            </a-list>
          </a-card>
        </a-col>
      </a-row>
    </a-card>

    <!-- 补充附件（出运锁定后显示，用于补充说明） -->
    <a-card v-if="locked" size="small" title="补充附件（补充说明，不受出运锁定限制）" style="margin-top:8px">
      <template #extra>
        <a-upload
          v-if="canEdit"
          :before-upload="(f) => beforeUpload(f, 'supplement')"
          :show-upload-list="false"
        >
          <a-button type="link" size="small">上传补充附件</a-button>
        </a-upload>
      </template>
      <a-empty v-if="!filesByType.supplement || filesByType.supplement.length === 0"
        :image="emptyImage" description="暂无补充附件" />
      <a-list v-else size="small" :data-source="filesByType.supplement">
        <template #renderItem="{ item }">
          <a-list-item>
            <a :href="`/uploads/${item.file_path}`" target="_blank">{{ item.file_name }}</a>
            <span style="color:#999; margin-left:12px">{{ (item.uploaded_at || '').slice(0,10) }}</span>
            <template #actions>
              <a-popconfirm v-if="canEdit" title="删除？" @confirm="delFile(item.id)">
                <a style="color:#ff4d4f">删除</a>
              </a-popconfirm>
            </template>
          </a-list-item>
        </template>
      </a-list>
    </a-card>

    <!-- 提单 编辑/创建 modal -->
    <a-modal v-model:open="blOpen" :title="blEditing ? '编辑提单' : '创建提单'" width="640" :confirm-loading="saving" @ok="submitBL">
      <a-form layout="vertical">
        <a-form-item label="运输方式">
          <a-radio-group v-model:value="blForm.ship_type">
            <a-radio value="container">集装箱</a-radio>
            <a-radio value="bulk">散货船</a-radio>
          </a-radio-group>
        </a-form-item>
        <a-row :gutter="12">
          <a-col :span="12"><a-form-item label="提单号"><a-input v-model:value="blForm.bl_number" /></a-form-item></a-col>
          <a-col :span="12"><a-form-item label="船名航次"><a-input v-model:value="blForm.vessel_voyage" /></a-form-item></a-col>
          <a-col :span="12"><a-form-item label="起运港"><a-input v-model:value="blForm.load_port" placeholder="如 Shanghai" /></a-form-item></a-col>
          <a-col :span="12"><a-form-item label="目的港"><a-input v-model:value="blForm.discharge_port" placeholder="如 Hamburg" /></a-form-item></a-col>
          <a-col :span="12"><a-form-item label="ETD"><a-date-picker v-model:value="blForm.etd" style="width:100%" value-format="YYYY-MM-DD" /></a-form-item></a-col>
          <a-col :span="12"><a-form-item label="ETA"><a-date-picker v-model:value="blForm.eta" style="width:100%" value-format="YYYY-MM-DD" /></a-form-item></a-col>
          <a-col v-if="blForm.ship_type === 'container'" :span="24">
            <a-form-item label="箱型箱量">
              <a-input v-model:value="blForm.container_info" placeholder="如 20GP*2，40HC*1" />
            </a-form-item>
          </a-col>
        </a-row>

        <template v-if="blForm.ship_type === 'bulk'">
          <a-row :gutter="12">
            <a-col :span="8"><a-form-item label="件数"><a-input-number v-model:value="blForm.pieces" style="width:100%" :min="0" /></a-form-item></a-col>
            <a-col :span="8"><a-form-item label="重量(MT)"><a-input-number v-model:value="blForm.weight_mt" style="width:100%" :min="0" /></a-form-item></a-col>
            <a-col :span="8"><a-form-item label="体积(CBM)"><a-input-number v-model:value="blForm.volume_cbm" style="width:100%" :min="0" /></a-form-item></a-col>
          </a-row>
        </template>

        <a-form-item label="备注"><a-textarea v-model:value="blForm.remarks" :rows="2" /></a-form-item>
      </a-form>
    </a-modal>

    <!-- 评价记录 -->
    <a-card v-if="order" size="small" style="margin-top: 16px">
      <EvaluationPanel
        target-type="formal_order"
        :target-id="order.id"
        :subject-id="order.salesperson.id"
      />
    </a-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { message, Empty } from 'ant-design-vue'
import { formalOrdersApi } from '@/api/inquiries'
import { useAuthStore } from '@/stores/auth'
import EvaluationPanel from '@/components/EvaluationPanel.vue'

const route = useRoute()
const auth = useAuthStore()
const emptyImage = Empty.PRESENTED_IMAGE_SIMPLE

const STATUS_LABEL = {
  confirmed: '已确认', production: '生产中', ready: '待出运',
  shipping: '出运中', completed: '已完结',
}
const STATUS_COLOR = {
  confirmed: 'blue', production: 'gold', ready: 'orange',
  shipping: 'cyan', completed: 'green',
}
const BL_STATUS_LABEL = { planned: '计划中', loaded: '已装柜', transit: '运输中', arrived: '已到港' }

const DOC_DEFS = [
  { key: 'mtc', label: 'MTC 质保书' },
  { key: 'pl', label: 'PL 装箱单' },
  { key: 'ci', label: 'CI 商业发票' },
  { key: 'co', label: 'CO 原产地证' },
  { key: 'export_permit', label: '出口许可证' },
  { key: 'inspection', label: '验货照片' },
  { key: 'packing', label: '装箱照片' },
]

const order = ref(null)
const bl = computed(() => order.value?.bls?.[0] || null)

const canEdit = computed(() => {
  if (!order.value) return false
  if (auth.hasRole('super_admin')) return true
  if (auth.hasRole('salesperson')) return order.value.salesperson.id === auth.user?.id
  return false
})

// 线性流转；现货订单跳过「生产中」
function computeNext(o) {
  if (!o) return null
  switch (o.status) {
    case 'confirmed': return o.is_stock ? 'ready' : 'production'
    case 'production': return 'ready'
    case 'ready': return 'shipping'
    case 'shipping': return 'completed'
    default: return null
  }
}
const nextStatus = computed(() => computeNext(order.value))

const locked = computed(() => ['shipping', 'completed'].includes(order.value?.status))

const advanceTitle = computed(() => {
  if (nextStatus.value === 'shipping') {
    return '推进到「出运中」后，已上传的归档文件将被锁定（仅可查看），只能再上传补充附件。确认推进？'
  }
  return `确认将订单推进到「${STATUS_LABEL[nextStatus.value]}」？`
})

const countdown = computed(() => {
  if (!order.value?.est_production_date) return null
  const target = new Date(order.value.est_production_date)
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return Math.round((target - today) / 86400000)
})

const filesByType = computed(() => {
  const map = {}
  for (const dt of DOC_DEFS) map[dt.key] = []
  for (const f of order.value?.files || []) {
    if (!map[f.doc_type]) map[f.doc_type] = []
    map[f.doc_type].push(f)
  }
  return map
})
function has(key) { return (filesByType.value[key] || []).length > 0 }

const reminder = computed(() => {
  const s = order.value?.status
  const hasBL = !!bl.value
  if (s === 'confirmed') {
    return {
      type: 'info', title: '已确认 —— 准备投产',
      items: [
        { text: '核对最终 PI、唛头、技术要求', done: false },
        { text: order.value.is_stock ? '现货订单，确认库存已锁定' : '非现货，确认预计生产完成日期已填写', done: order.value.is_stock || !!order.value.est_production_date },
      ],
    }
  }
  if (s === 'production') {
    return {
      type: 'info', title: '生产中 —— 建议归档以下文件',
      items: [
        { text: '验货照片（建议）', done: has('inspection') },
        { text: 'MTC 质保书（可提前归档）', done: has('mtc') },
        { text: '安排验货 / 跟踪生产进度', done: false },
      ],
    }
  }
  if (s === 'ready') {
    return {
      type: has('pl') && has('ci') ? 'success' : 'error',
      title: '待出运 —— 出运前请备齐',
      items: [
        { text: 'PL 装箱单（必备）', done: has('pl') },
        { text: 'CI 商业发票（必备）', done: has('ci') },
        { text: 'CO 原产地证 / 出口许可证（按需）', done: has('co') || has('export_permit') },
        { text: '装箱照片（建议）', done: has('packing') },
        { text: 'MTC 质保书', done: has('mtc') },
      ],
    }
  }
  if (s === 'shipping') {
    return {
      type: hasBL ? 'success' : 'warning',
      title: '出运中 —— 完善提单与集装箱',
      items: [
        { text: '录入提单(BL)信息', done: hasBL },
        { text: '维护起运港 / 目的港、船名航次、ETD/ETA', done: false },
      ],
    }
  }
  return {
    type: 'success', title: '已完结 —— 确认归档完整',
    items: [
      { text: 'MTC 已归档', done: has('mtc') },
      { text: 'PL / CI 已归档', done: has('pl') && has('ci') },
      { text: '提单信息完整', done: hasBL },
    ],
  }
})

async function load() {
  const res = await formalOrdersApi.get(route.params.id)
  order.value = res.data
}

async function advance() {
  await formalOrdersApi.setStatus(order.value.id, nextStatus.value)
  message.success('状态已推进')
  await load()
}

async function beforeUpload(file, docType) {
  try {
    await formalOrdersApi.uploadFile(order.value.id, docType, file)
    message.success('上传成功')
    await load()
  } catch { /* 拦截器已提示 */ }
  return false
}

async function delFile(fileId) {
  await formalOrdersApi.deleteFile(order.value.id, fileId)
  message.success('已删除')
  await load()
}

// ── 提单 ──
const blOpen = ref(false)
const blEditing = ref(false)
const saving = ref(false)
const blForm = ref(null)

function openBL(editing) {
  blEditing.value = editing
  if (editing && bl.value) {
    const b = bl.value
    blForm.value = {
      ship_type: b.ship_type, bl_number: b.bl_number || '', vessel_voyage: b.vessel_voyage || '',
      container_info: b.container_info || '',
      load_port: b.load_port || '', discharge_port: b.discharge_port || '',
      etd: b.etd || null, eta: b.eta || null,
      pieces: b.pieces, weight_mt: b.weight_mt, volume_cbm: b.volume_cbm,
      remarks: b.remarks || '',
    }
  } else {
    blForm.value = {
      ship_type: 'container', bl_number: '', vessel_voyage: '',
      container_info: '',
      load_port: '', discharge_port: '', etd: null, eta: null,
      pieces: null, weight_mt: null, volume_cbm: null, remarks: '',
    }
  }
  blOpen.value = true
}

async function submitBL() {
  saving.value = true
  try {
    const f = blForm.value
    const payload = {
      ship_type: f.ship_type,
      bl_number: f.bl_number || null,
      vessel_voyage: f.vessel_voyage || null,
      container_info: f.ship_type === 'container' ? (f.container_info || null) : null,
      load_port: f.load_port || null,
      discharge_port: f.discharge_port || null,
      etd: f.etd || null,
      eta: f.eta || null,
      remarks: f.remarks || null,
      pieces: f.ship_type === 'bulk' ? f.pieces : null,
      weight_mt: f.ship_type === 'bulk' ? f.weight_mt : null,
      volume_cbm: f.ship_type === 'bulk' ? f.volume_cbm : null,
    }
    if (blEditing.value) {
      await formalOrdersApi.updateBL(order.value.id, bl.value.id, payload)
      message.success('已更新提单')
    } else {
      await formalOrdersApi.addBL(order.value.id, payload)
      message.success('已创建提单')
    }
    blOpen.value = false
    await load()
  } finally {
    saving.value = false
  }
}

async function changeBLStatus(status) {
  await formalOrdersApi.updateBL(order.value.id, bl.value.id, { status })
  message.success('状态已更新')
  await load()
}

async function delBL() {
  await formalOrdersApi.deleteBL(order.value.id, bl.value.id)
  message.success('已删除提单')
  await load()
}

onMounted(load)
</script>
