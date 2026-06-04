<template>
  <div v-if="inq">
    <a-page-header :title="inq.enq_number" @back="$router.back()">
      <template #tags>
        <a-tag :color="STATUS_COLOR[inq.status]">{{ STATUS_LABEL[inq.status] }}</a-tag>
      </template>
      <template #extra>
        <a-tooltip
          v-if="canEdit && inq.status === 'active'"
          :title="canDeposit ? '' : '请先上传核价单和 PI 当前版本'"
        >
          <a-button :disabled="!canDeposit" @click="openDeposit">登记定金</a-button>
        </a-tooltip>
        <a-button
          v-if="canEdit && inq.status === 'deposit_received'"
          type="primary"
          @click="openConvert"
        >转为正式订单</a-button>
        <a-button
          v-if="inq.status === 'converted' && inq.formal_order_id"
          type="link"
          @click="$router.push({ name: 'OrderDetail', params: { id: inq.formal_order_id } })"
        >查看订单 →</a-button>
        <a-popconfirm
          v-if="canEdit && ['active','deposit_received'].includes(inq.status)"
          title="确认作废该询价单？"
          @confirm="doVoid"
        >
          <a-button danger>作废</a-button>
        </a-popconfirm>
      </template>
      <a-descriptions size="small" :column="3">
        <a-descriptions-item label="客户">{{ inq.customer.company_name }}</a-descriptions-item>
        <a-descriptions-item label="业务员">{{ inq.salesperson.full_name }}</a-descriptions-item>
        <a-descriptions-item label="创建时间">{{ (inq.created_at || '').slice(0,10) }}</a-descriptions-item>
        <a-descriptions-item v-if="inq.deposit_amount != null" label="定金金额">
          {{ Number(inq.deposit_amount).toLocaleString() }}
        </a-descriptions-item>
        <a-descriptions-item v-if="inq.deposit_date" label="定金日期">{{ inq.deposit_date }}</a-descriptions-item>
        <a-descriptions-item label="备注">{{ inq.remarks || '—' }}</a-descriptions-item>
      </a-descriptions>
    </a-page-header>

    <!-- 节点提醒 -->
    <a-alert
      :type="reminder.type"
      show-icon
      style="margin:16px 0"
      :message="reminder.title"
    >
      <template #description>
        <ul style="margin:4px 0 0; padding-left:18px">
          <li v-for="(item, i) in reminder.items" :key="i" :style="{ color: item.done ? '#52c41a' : '#fa541c' }">
            {{ item.done ? '✓' : '○' }} {{ item.text }}
          </li>
        </ul>
      </template>
    </a-alert>

    <!-- 文件区 -->
    <a-row :gutter="16">
      <a-col v-for="dt in DOC_DEFS" :key="dt.key" :span="8">
        <a-card size="small" :title="dt.label" style="margin-bottom:16px">
          <template #extra>
            <a-upload
              v-if="canEdit && inq.status !== 'converted' && inq.status !== 'void'"
              :before-upload="(f) => beforeUpload(f, dt.key)"
              :show-upload-list="false"
            >
              <a-button type="link" size="small">上传新版本</a-button>
            </a-upload>
          </template>

          <a-empty v-if="!filesByType[dt.key] || filesByType[dt.key].length === 0"
            :image="emptyImage" description="暂无文件" />
          <a-list v-else size="small" :data-source="filesByType[dt.key]">
            <template #renderItem="{ item }">
              <a-list-item>
                <a-list-item-meta>
                  <template #title>
                    <a :href="`/uploads/${item.file_path}`" target="_blank">{{ item.file_name }}</a>
                    <a-tag v-if="item.is_current" color="green" style="margin-left:8px">当前 v{{ item.version }}</a-tag>
                    <a-tag v-else style="margin-left:8px">v{{ item.version }}</a-tag>
                  </template>
                  <template #description>
                    {{ (item.uploaded_at || '').slice(0,10) }}
                    <span v-if="item.note"> · {{ item.note }}</span>
                  </template>
                </a-list-item-meta>
                <template #actions>
                  <a-popconfirm v-if="canEdit" title="删除该版本？" @confirm="delFile(item.id)">
                    <a style="color:#ff4d4f">删除</a>
                  </a-popconfirm>
                </template>
              </a-list-item>
            </template>
          </a-list>
        </a-card>
      </a-col>
    </a-row>

    <!-- 登记定金 -->
    <a-modal v-model:open="depositOpen" title="登记定金" :confirm-loading="saving" @ok="doDeposit">
      <a-form layout="vertical">
        <a-form-item label="定金金额" required>
          <a-input-number v-model:value="depositForm.amount" style="width:100%" :min="0" />
        </a-form-item>
        <a-form-item label="到账日期">
          <a-date-picker v-model:value="depositForm.date" style="width:100%" value-format="YYYY-MM-DD" />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 转订单 -->
    <a-modal v-model:open="convertOpen" title="转为正式订单" :confirm-loading="saving" @ok="doConvert">
      <a-form layout="vertical">
        <a-form-item label="货物类型">
          <a-radio-group v-model:value="convertForm.is_stock">
            <a-radio :value="true">现货</a-radio>
            <a-radio :value="false">非现货（需生产）</a-radio>
          </a-radio-group>
        </a-form-item>
        <a-form-item v-if="!convertForm.is_stock" label="预计生产完成日期">
          <a-date-picker v-model:value="convertForm.est_production_date" style="width:100%" value-format="YYYY-MM-DD" />
        </a-form-item>
        <a-form-item label="备注">
          <a-textarea v-model:value="convertForm.remarks" :rows="2" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message, Empty } from 'ant-design-vue'
import { inquiriesApi, formalOrdersApi } from '@/api/inquiries'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const emptyImage = Empty.PRESENTED_IMAGE_SIMPLE

const STATUS_LABEL = {
  active: '进行中', deposit_received: '已收定金',
  converted: '已转订单', void: '已失效',
}
const STATUS_COLOR = {
  active: 'orange', deposit_received: 'green',
  converted: 'blue', void: 'default',
}

const DOC_DEFS = [
  { key: 'pricing_sheet', label: '核价单', required: true },
  { key: 'pi', label: 'PI', required: true },
  { key: 'freight_quote', label: '货代海运费', required: false },
]

const inq = ref(null)

const canEdit = computed(() => {
  if (!inq.value) return false
  if (auth.hasRole('super_admin')) return true
  if (auth.hasRole('salesperson')) return inq.value.salesperson.id === auth.user?.id
  return false
})

const filesByType = computed(() => {
  const map = {}
  for (const dt of DOC_DEFS) map[dt.key] = []
  for (const f of inq.value?.files || []) {
    if (!map[f.doc_type]) map[f.doc_type] = []
    map[f.doc_type].push(f)
  }
  // 当前版本在前，再按版本号倒序
  for (const k in map) {
    map[k].sort((a, b) => b.version - a.version)
  }
  return map
})

function hasCurrent(key) {
  return (filesByType.value[key] || []).some((f) => f.is_current)
}

const canDeposit = computed(() => hasCurrent('pricing_sheet') && hasCurrent('pi'))

const reminder = computed(() => {
  const s = inq.value?.status
  if (s === 'active') {
    return {
      type: hasCurrent('pricing_sheet') && hasCurrent('pi') ? 'success' : 'warning',
      title: '进行中 —— 请准备以下文件',
      items: [
        { text: '核价单（必备）', done: hasCurrent('pricing_sheet') },
        { text: 'PI 形式发票（必备）', done: hasCurrent('pi') },
        { text: '货代海运费报价（可选）', done: hasCurrent('freight_quote') },
        { text: '收到定金后点击「登记定金」即可转正式订单', done: false },
      ],
    }
  }
  if (s === 'deposit_received') {
    return {
      type: 'success',
      title: '已收定金 —— 可转为正式订单',
      items: [
        { text: '核对最终 PI 与定金金额无误', done: hasCurrent('pi') },
        { text: '点击右上角「转为正式订单」继续流程', done: false },
      ],
    }
  }
  if (s === 'converted') {
    return { type: 'info', title: '已转为正式订单', items: [{ text: '后续操作请前往对应正式订单', done: true }] }
  }
  return { type: 'error', title: '已失效', items: [{ text: '该询价单已作废，仅作历史归档', done: true }] }
})

async function load() {
  const res = await inquiriesApi.get(route.params.id)
  inq.value = res.data
}

async function beforeUpload(file, docType) {
  try {
    await inquiriesApi.uploadFile(inq.value.id, docType, file)
    message.success('上传成功')
    await load()
  } catch { /* 拦截器已提示 */ }
  return false
}

async function delFile(fileId) {
  await inquiriesApi.deleteFile(inq.value.id, fileId)
  message.success('已删除')
  await load()
}

// ── 定金 ──
const depositOpen = ref(false)
const saving = ref(false)
const depositForm = ref({ amount: null, date: null })
function openDeposit() {
  depositForm.value = { amount: null, date: null }
  depositOpen.value = true
}
async function doDeposit() {
  if (!depositForm.value.amount) {
    message.warning('请输入定金金额')
    return
  }
  saving.value = true
  try {
    await inquiriesApi.setDeposit(inq.value.id, {
      deposit_amount: depositForm.value.amount,
      deposit_date: depositForm.value.date || null,
    })
    message.success('已登记定金')
    depositOpen.value = false
    await load()
  } finally {
    saving.value = false
  }
}

// ── 转订单 ──
const convertOpen = ref(false)
const convertForm = ref({ is_stock: true, est_production_date: null, remarks: '' })
function openConvert() {
  convertForm.value = { is_stock: true, est_production_date: null, remarks: '' }
  convertOpen.value = true
}
async function doConvert() {
  saving.value = true
  try {
    const res = await formalOrdersApi.convert({
      inquiry_id: inq.value.id,
      is_stock: convertForm.value.is_stock,
      est_production_date: convertForm.value.is_stock ? null : convertForm.value.est_production_date,
      remarks: convertForm.value.remarks || null,
    })
    message.success('已转为正式订单')
    convertOpen.value = false
    router.push({ name: 'OrderDetail', params: { id: res.data.id } })
  } finally {
    saving.value = false
  }
}

async function doVoid() {
  await inquiriesApi.void(inq.value.id)
  message.success('已作废')
  await load()
}

onMounted(load)
</script>
