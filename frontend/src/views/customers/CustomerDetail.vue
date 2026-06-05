<template>
  <div>
    <!-- 返回 + 标题 -->
    <div class="page-header">
      <a-space>
        <a-button @click="router.back()">← 返回</a-button>
        <a-typography-title :level="4" style="margin: 0">
          {{ customer?.company_name }}
        </a-typography-title>
      </a-space>
      <a-button v-if="canEdit" type="primary" ghost @click="openEdit">编辑客户</a-button>
    </div>

    <a-spin :spinning="loading">
      <template v-if="customer">
        <!-- 客户基本信息 -->
        <a-card style="margin-bottom: 16px">
          <a-descriptions :column="3" bordered size="small">
            <a-descriptions-item label="公司名称">{{ customer.company_name }}</a-descriptions-item>
            <a-descriptions-item label="国家">{{ customer.country }}</a-descriptions-item>
            <a-descriptions-item label="联系人">{{ customer.contact_name }}</a-descriptions-item>
            <a-descriptions-item label="邮箱">{{ customer.email || '-' }}</a-descriptions-item>
            <a-descriptions-item label="电话">{{ customer.phone || '-' }}</a-descriptions-item>
            <a-descriptions-item label="贸易条款">{{ customer.trade_terms || '-' }}</a-descriptions-item>
            <a-descriptions-item label="付款方式">{{ customer.payment_terms || '-' }}</a-descriptions-item>
            <a-descriptions-item label="客户分级">
              <a-tag :color="gradeColor(customer.grade)">{{ gradeLabel(customer.grade) }}</a-tag>
            </a-descriptions-item>
            <a-descriptions-item label="负责人">{{ customer.owner.full_name }}</a-descriptions-item>
          </a-descriptions>

          <!-- 跟进频次 -->
          <div class="freq-bar">
            <span>跟进频次：</span>
            <a-tag :color="freqColor(customer.follow_freq)">{{ freqLabel(customer.follow_freq) }}</a-tag>
            <a-dropdown v-if="canEdit && customer.follow_freq !== 'daily'">
              <a-button size="small" type="link">手动升级 ↑</a-button>
              <template #overlay>
                <a-menu @click="handleUpgradeFreq">
                  <a-menu-item v-if="customer.follow_freq === 'monthly'" key="weekly">升级至每周</a-menu-item>
                  <a-menu-item v-if="customer.follow_freq !== 'daily'" key="daily">升级至每日</a-menu-item>
                </a-menu>
              </template>
            </a-dropdown>
          </div>
        </a-card>

        <!-- 跟进记录 -->
        <a-card title="跟进记录">
          <template v-if="canAddFollowUp" #extra>
            <a-button type="primary" size="small" @click="showFollowUpForm = !showFollowUpForm">
              {{ showFollowUpForm ? '收起' : '+ 添加跟进' }}
            </a-button>
          </template>

          <div v-if="showFollowUpForm" class="followup-form">
            <a-form layout="vertical">
              <a-form-item label="跟进内容" required>
                <a-textarea
                  v-model:value="followUpForm.content"
                  :rows="4"
                  placeholder="记录本次跟进情况..."
                />
              </a-form-item>

              <a-form-item>
                <a-radio-group v-model:value="followUpForm.is_effective">
                  <a-radio :value="true">有效跟进</a-radio>
                  <a-radio :value="false">无效跟进</a-radio>
                </a-radio-group>
              </a-form-item>

              <a-form-item label="上传截图/图片（可多张）">
                <a-upload
                  v-model:file-list="followUpForm.fileList"
                  list-type="picture-card"
                  :before-upload="() => false"
                  accept="image/*"
                  multiple
                >
                  <div>
                    <plus-outlined />
                    <div style="margin-top: 8px">上传</div>
                  </div>
                </a-upload>
              </a-form-item>

              <a-button type="primary" :loading="submittingFollowUp" @click="submitFollowUp">
                提交跟进记录
              </a-button>
            </a-form>
          </div>

          <a-spin :spinning="loadingFollowUps">
            <a-empty v-if="!followUps.length && !loadingFollowUps" description="暂无跟进记录" />
            <a-timeline v-if="followUps.length" style="margin-top: 16px">
              <a-timeline-item
                v-for="item in followUps"
                :key="item.id"
                :color="item.is_effective ? 'green' : 'gray'"
              >
                <div class="followup-item">
                  <div class="followup-meta">
                    <a-tag :color="item.is_effective ? 'success' : 'default'" size="small">
                      {{ item.is_effective ? '有效' : '无效' }}
                    </a-tag>
                    <span class="followup-date">{{ item.created_at }}</span>
                  </div>
                  <p class="followup-content">{{ item.content }}</p>
                  <div v-if="item.images?.length" class="followup-images">
                    <a-image
                      v-for="img in item.images"
                      :key="img.id"
                      :src="img.file_path"
                      :width="80"
                      :height="80"
                      :preview="{ src: img.file_path }"
                      style="border-radius: 4px; object-fit: cover; cursor: pointer"
                    />
                  </div>
                  <EvaluationPanel
                    target-type="followup"
                    :target-id="item.id"
                    :subject-id="item.created_by"
                  />
                </div>
              </a-timeline-item>
            </a-timeline>

            <div v-if="followUpTotal > pageSize" class="pagination-bar">
              <a-pagination
                v-model:current="currentPage"
                :total="followUpTotal"
                :page-size="pageSize"
                :show-total="(t) => `共 ${t} 条`"
                size="small"
                @change="onPageChange"
              />
            </div>
          </a-spin>
        </a-card>
      </template>
    </a-spin>

    <!-- 编辑客户弹窗 -->
    <a-modal
      v-model:open="editModalVisible"
      title="编辑客户"
      :confirm-loading="saving"
      @ok="handleSaveEdit"
      @cancel="editModalVisible = false"
    >
      <a-form ref="editFormRef" :model="editForm" :rules="editRules" layout="vertical" style="margin-top: 16px">
        <a-form-item label="公司名称" name="company_name">
          <a-input v-model:value="editForm.company_name" />
        </a-form-item>
        <a-form-item label="国家" name="country">
          <a-input v-model:value="editForm.country" />
        </a-form-item>
        <a-form-item label="联系人" name="contact_name">
          <a-input v-model:value="editForm.contact_name" />
        </a-form-item>
        <a-form-item label="邮箱">
          <a-input v-model:value="editForm.email" />
        </a-form-item>
        <a-form-item label="电话">
          <a-input v-model:value="editForm.phone" />
        </a-form-item>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="贸易条款">
              <a-select v-model:value="editForm.trade_terms" allow-clear>
                <a-select-option v-for="t in TRADE_TERMS" :key="t" :value="t">{{ t }}</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="付款方式">
              <a-input v-model:value="editForm.payment_terms" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="客户分级" name="grade">
          <a-radio-group v-model:value="editForm.grade">
            <a-radio-button value="key">重点</a-radio-button>
            <a-radio-button value="normal">普通</a-radio-button>
            <a-radio-button value="potential">潜在</a-radio-button>
          </a-radio-group>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { PlusOutlined } from '@ant-design/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { customersApi } from '@/api/customers'
import EvaluationPanel from '@/components/EvaluationPanel.vue'

const TRADE_TERMS = ['EXW', 'FOB', 'CFR', 'CIF', 'DAP', 'DDP']

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const customerId = Number(route.params.id)

const customer = ref(null)
const loading = ref(false)
const followUps = ref([])
const loadingFollowUps = ref(false)
const followUpTotal = ref(0)
const currentPage = ref(1)
const pageSize = 5
const showFollowUpForm = ref(false)
const submittingFollowUp = ref(false)

const editModalVisible = ref(false)
const saving = ref(false)
const editFormRef = ref()

const followUpForm = reactive({
  content: '',
  is_effective: true,
  fileList: [],
})

const editForm = reactive({
  company_name: '',
  country: '',
  contact_name: '',
  email: '',
  phone: '',
  trade_terms: undefined,
  payment_terms: '',
  grade: 'potential',
})

const editRules = {
  company_name: [{ required: true, message: '请输入公司名称' }],
  country: [{ required: true, message: '请输入国家' }],
  contact_name: [{ required: true, message: '请输入联系人' }],
}

const canEdit = computed(() => {
  if (!customer.value) return false
  if (auth.hasRole('super_admin')) return true
  return auth.user?.id === customer.value.owner.id
})

const canAddFollowUp = computed(() =>
  auth.hasRole('salesperson', 'super_admin') && canEdit.value
)

function gradeColor(g) {
  return { key: 'red', normal: 'blue', potential: 'default' }[g] || 'default'
}
function gradeLabel(g) {
  return { key: '重点', normal: '普通', potential: '潜在' }[g] || g
}
function freqColor(f) {
  return { daily: 'green', weekly: 'blue', monthly: 'orange' }[f] || 'default'
}
function freqLabel(f) {
  return { daily: '每日', weekly: '每周', monthly: '每月' }[f] || f
}

async function loadCustomer() {
  loading.value = true
  try {
    const res = await customersApi.get(customerId)
    customer.value = res.data
  } finally {
    loading.value = false
  }
}

async function loadFollowUps(page = currentPage.value) {
  loadingFollowUps.value = true
  try {
    const res = await customersApi.listFollowUps(customerId, page, pageSize)
    followUps.value = res.data.items
    followUpTotal.value = res.data.total
    currentPage.value = res.data.page
  } finally {
    loadingFollowUps.value = false
  }
}

function onPageChange(page) {
  loadFollowUps(page)
}

async function submitFollowUp() {
  if (!followUpForm.content.trim()) {
    message.warning('请输入跟进内容')
    return
  }

  submittingFollowUp.value = true
  try {
    const fd = new FormData()
    fd.append('content', followUpForm.content)
    fd.append('is_effective', String(followUpForm.is_effective))
    for (const f of followUpForm.fileList) {
      fd.append('images', f.originFileObj)
    }
    await customersApi.createFollowUp(customerId, fd)
    message.success('跟进记录已添加')
    followUpForm.content = ''
    followUpForm.is_effective = true
    followUpForm.fileList = []
    showFollowUpForm.value = false
    currentPage.value = 1
    await Promise.all([loadFollowUps(1), loadCustomer()])
  } finally {
    submittingFollowUp.value = false
  }
}

async function handleUpgradeFreq({ key }) {
  try {
    await customersApi.upgradeFreq(customerId, key)
    message.success('跟进频次已升级')
    await loadCustomer()
  } catch {
    // 错误由拦截器处理
  }
}

function openEdit() {
  const c = customer.value
  editForm.company_name = c.company_name
  editForm.country = c.country
  editForm.contact_name = c.contact_name
  editForm.email = c.email || ''
  editForm.phone = c.phone || ''
  editForm.trade_terms = c.trade_terms || undefined
  editForm.payment_terms = c.payment_terms || ''
  editForm.grade = c.grade
  editModalVisible.value = true
}

async function handleSaveEdit() {
  try {
    await editFormRef.value.validate()
  } catch {
    return
  }
  saving.value = true
  try {
    await customersApi.update(customerId, {
      company_name: editForm.company_name,
      country: editForm.country,
      contact_name: editForm.contact_name,
      email: editForm.email || null,
      phone: editForm.phone || null,
      trade_terms: editForm.trade_terms || null,
      payment_terms: editForm.payment_terms || null,
      grade: editForm.grade,
    })
    message.success('客户信息已更新')
    editModalVisible.value = false
    await loadCustomer()
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadCustomer()
  loadFollowUps()
})
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.freq-bar {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.followup-form {
  background: #fafafa;
  border: 1px solid #f0f0f0;
  border-radius: 6px;
  padding: 16px;
  margin-bottom: 16px;
}
.followup-item {
  padding-bottom: 4px;
}
.followup-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.followup-date {
  color: #999;
  font-size: 12px;
}
.followup-content {
  margin: 0 0 8px;
  white-space: pre-wrap;
}
.followup-images {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}
.followup-images :deep(.ant-image-img) {
  width: 80px;
  height: 80px;
  object-fit: cover;
  border-radius: 4px;
}
.pagination-bar {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
}
</style>
