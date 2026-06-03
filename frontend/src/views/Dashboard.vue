<template>
  <div>
    <!-- 置顶公告 -->
    <div v-if="announcements.length" class="announcements">
      <a-alert
        v-for="ann in announcements"
        :key="ann.id"
        type="warning"
        show-icon
        :closable="canRevoke(ann)"
        class="ann-item"
        @close="revokeAnnouncement(ann.id)"
      >
        <template #message>
          <span>{{ ann.content }}</span>
          <span class="ann-meta">— {{ ann.creator_name }} {{ formatDate(ann.created_at) }}</span>
        </template>
      </a-alert>
    </div>

    <!-- 发布公告按钮 -->
    <div v-if="auth.hasRole('boss', 'purchaser', 'super_admin')" class="publish-row">
      <a-button type="primary" ghost @click="showPublish = true">
        <template #icon><notification-outlined /></template>
        发布置顶通知
      </a-button>
    </div>

    <!-- ====== 老板 / 超管看板 ====== -->
    <template v-if="auth.hasRole('boss', 'super_admin')">
      <a-row :gutter="16" class="stat-row">
        <a-col :span="6">
          <a-card class="stat-card">
            <a-statistic
              title="今日全员跟进客户数"
              :value="bossData.today_follow_count ?? 0"
              :value-style="{ color: '#1677ff', cursor: 'pointer' }"
              @click="$router.push('/customers?today_follow=1')"
            />
          </a-card>
        </a-col>
        <a-col :span="6">
          <a-card class="stat-card">
            <a-statistic
              title="今日有效跟进数"
              :value="bossData.today_effective_follow_count ?? 0"
              :value-style="{ color: '#52c41a', cursor: 'pointer' }"
              @click="$router.push('/follow-ups?today=1&effective=1')"
            />
          </a-card>
        </a-col>
        <a-col :span="6">
          <a-card class="stat-card">
            <a-statistic title="进行中订单" :value="bossData.active_orders?.length ?? 0" />
          </a-card>
        </a-col>
        <a-col :span="6">
          <a-card class="stat-card">
            <a-statistic title="本月出运计划" :value="bossData.shipment_plan?.length ?? 0" />
          </a-card>
        </a-col>
      </a-row>

      <a-row :gutter="16" style="margin-top: 16px">
        <!-- 今日跟进摘要（仅有效） -->
        <a-col :span="12">
          <a-card size="small">
            <template #title>今日跟进摘要（有效）</template>
            <template #extra>
              <a-button
                v-if="bossData.follow_summary?.length"
                type="link"
                size="small"
                @click="openFollowSummaryModal"
              >显示全部</a-button>
            </template>
            <a-empty v-if="!bossData.follow_summary?.length" description="今日暂无有效跟进" />
            <a-list
              v-else
              :data-source="bossData.follow_summary.slice(0, 5)"
              size="small"
            >
              <template #renderItem="{ item }">
                <a-list-item>
                  <a-list-item-meta>
                    <template #title>
                      <router-link :to="`/customers/${item.customer_id}`">
                        {{ item.customer_name }}
                      </router-link>
                      <span class="creator-tag">{{ item.creator_name }}</span>
                    </template>
                    <template #description>{{ item.content.length > 60 ? item.content.slice(0, 60) + '…' : item.content }}</template>
                  </a-list-item-meta>
                  <template #extra>{{ formatDate(item.created_at) }}</template>
                </a-list-item>
              </template>
            </a-list>
          </a-card>
        </a-col>

        <!-- 进行中订单总览 -->
        <a-col :span="12">
          <a-card size="small">
            <template #title>进行中订单总览</template>
            <template #extra>
              <a-button
                v-if="bossData.active_orders?.length"
                type="link"
                size="small"
                @click="showAllOrders = true"
              >显示全部</a-button>
            </template>
            <a-empty v-if="!bossData.active_orders?.length" description="暂无进行中订单" />
            <a-table
              v-else
              :data-source="bossData.active_orders.slice(0, 5)"
              :columns="orderColumns"
              :pagination="false"
              size="small"
              row-key="id"
            />
          </a-card>
        </a-col>
      </a-row>

      <!-- 各状态订单统计 -->
      <a-card title="各状态订单统计" size="small" style="margin-top: 16px">
        <a-row :gutter="8">
          <a-col v-for="(count, st) in bossData.order_status_counts" :key="st" :span="4">
            <a-statistic :title="ORDER_STATUS_LABELS[st] || st" :value="count" />
          </a-col>
        </a-row>
      </a-card>
    </template>

    <!-- ====== 业务员看板 ====== -->
    <template v-else-if="auth.hasRole('salesperson')">
      <a-row :gutter="16" class="stat-row">
        <a-col :span="8">
          <a-card class="stat-card">
            <a-statistic title="今日待跟进" :value="salesData.due_today_customers?.length ?? 0" />
          </a-card>
        </a-col>
        <a-col :span="8">
          <a-card class="stat-card">
            <a-statistic
              title="我的客户总数"
              :value="salesData.my_customer_count ?? 0"
              :value-style="{ color: '#1677ff', cursor: 'pointer' }"
              @click="$router.push('/customers')"
            />
          </a-card>
        </a-col>
        <a-col :span="8">
          <a-card class="stat-card">
            <a-statistic
              title="今日已跟进"
              :value="salesData.today_follow_count ?? 0"
              :value-style="{ color: '#52c41a', cursor: 'pointer' }"
              @click="$router.push('/follow-ups?today=1')"
            />
          </a-card>
        </a-col>
      </a-row>

      <a-row :gutter="16" style="margin-top: 16px">
        <!-- 今日应跟进客户（最多5条） -->
        <a-col :span="12">
          <a-card size="small">
            <template #title>今日应跟进客户</template>
            <template #extra>
              <a-button
                v-if="salesData.due_today_customers?.length"
                type="link"
                size="small"
                @click="showAllDueToday = true"
              >显示全部</a-button>
            </template>
            <a-empty v-if="!salesData.due_today_customers?.length" description="今日无待跟进客户" />
            <a-list
              v-else
              :data-source="salesData.due_today_customers.slice(0, 5)"
              size="small"
            >
              <template #renderItem="{ item }">
                <a-list-item>
                  <a-list-item-meta>
                    <template #title>
                      <router-link :to="`/customers/${item.id}`">{{ item.company_name }}</router-link>
                    </template>
                    <template #description>
                      {{ item.country }} · {{ GRADE_LABELS[item.grade] }} · {{ FREQ_LABELS[item.follow_freq] }}
                    </template>
                  </a-list-item-meta>
                  <template #extra>
                    <a-button size="small" @click="$router.push(`/customers/${item.id}`)">去跟进</a-button>
                  </template>
                </a-list-item>
              </template>
            </a-list>
          </a-card>
        </a-col>

        <!-- 我的进行中订单 -->
        <a-col :span="12">
          <a-card size="small">
            <template #title>我的进行中订单</template>
            <template #extra>
              <a-button
                v-if="salesData.active_orders?.length"
                type="link"
                size="small"
                @click="showAllOrders = true"
              >显示全部</a-button>
            </template>
            <a-empty v-if="!salesData.active_orders?.length" description="暂无进行中订单" />
            <a-table
              v-else
              :data-source="salesData.active_orders.slice(0, 5)"
              :columns="orderColumns"
              :pagination="false"
              size="small"
              row-key="id"
            />
          </a-card>
        </a-col>
      </a-row>
    </template>

    <!-- 采购员看板（仅公告） -->
    <template v-else-if="auth.hasRole('purchaser')">
      <a-empty description="采购员暂无看板数据" style="margin-top: 48px" />
    </template>

    <!-- ====== 弹窗：今日有效跟进摘要全部（老板） ====== -->
    <a-modal
      v-model:open="showAllFollowSummary"
      title="今日有效跟进摘要（全部）"
      :footer="null"
      width="780px"
      destroy-on-close
    >
      <div style="margin-bottom: 12px">
        <a-input-search
          v-model:value="followSummarySearch"
          placeholder="按创建人姓名搜索"
          style="width: 220px"
          allow-clear
        />
      </div>
      <a-table
        :data-source="filteredFollowSummary"
        :columns="followSummaryColumns"
        :pagination="{ pageSize: 10, showTotal: t => `共 ${t} 条` }"
        size="small"
        row-key="id"
      />
    </a-modal>

    <!-- ====== 弹窗：进行中订单全部（老板 + 业务员共用） ====== -->
    <a-modal
      v-model:open="showAllOrders"
      title="进行中订单（全部）"
      :footer="null"
      width="800px"
    >
      <a-table
        :data-source="allOrdersData"
        :columns="orderColumnsDetail"
        :pagination="{ pageSize: 10 }"
        size="small"
        row-key="id"
      />
    </a-modal>

    <!-- ====== 弹窗：今日应跟进客户全部（业务员） ====== -->
    <a-modal
      v-model:open="showAllDueToday"
      title="今日应跟进客户（全部）"
      :footer="null"
      width="700px"
      destroy-on-close
    >
      <a-table
        :data-source="salesData.due_today_customers"
        :columns="dueTodayColumns"
        :pagination="{ pageSize: 10, showTotal: t => `共 ${t} 条` }"
        size="small"
        row-key="id"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'company_name'">
            <a @click="$router.push(`/customers/${record.id}`); showAllDueToday = false">
              {{ record.company_name }}
            </a>
          </template>
          <template v-else-if="column.key === 'action'">
            <a-button size="small" @click="$router.push(`/customers/${record.id}`); showAllDueToday = false">
              去跟进
            </a-button>
          </template>
        </template>
      </a-table>
    </a-modal>

    <!-- ====== 弹窗：发布公告 ====== -->
    <a-modal
      v-model:open="showPublish"
      title="发布置顶通知"
      @ok="submitAnnouncement"
      :confirm-loading="publishing"
    >
      <a-textarea
        v-model:value="newContent"
        placeholder="请输入通知内容"
        :rows="4"
        :maxlength="500"
        show-count
      />
    </a-modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { NotificationOutlined } from '@ant-design/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { dashboardApi } from '@/api/dashboard'
import { announcementsApi } from '@/api/announcements'

const auth = useAuthStore()

const announcements = ref([])
const bossData = ref({})
const salesData = ref({})

const showPublish = ref(false)
const newContent = ref('')
const publishing = ref(false)

const showAllFollowSummary = ref(false)
const showAllOrders = ref(false)
const showAllDueToday = ref(false)
const followSummarySearch = ref('')

const ORDER_STATUS_LABELS = {
  confirmed: '已确认',
  production: '生产备货中',
  pending_shipment: '待出运',
  shipped: '已出运',
  completed: '已完结',
}
const GRADE_LABELS = { key: '重点', normal: '普通', potential: '潜在' }
const FREQ_LABELS = { daily: '每日', weekly: '每周', monthly: '每月' }

const orderColumns = [
  { title: '订单号', dataIndex: 'so_number', key: 'so_number' },
  {
    title: '状态',
    dataIndex: 'status',
    key: 'status',
    customRender: ({ text }) => ORDER_STATUS_LABELS[text] || text,
  },
  {
    title: '预计完成',
    dataIndex: 'est_ready_date',
    key: 'est_ready_date',
    customRender: ({ text }) => text || '-',
  },
]

const orderColumnsDetail = [
  { title: '订单号', dataIndex: 'so_number', key: 'so_number' },
  {
    title: '状态',
    dataIndex: 'status',
    key: 'status',
    customRender: ({ text }) => ORDER_STATUS_LABELS[text] || text,
  },
  {
    title: '预计完成',
    dataIndex: 'est_ready_date',
    key: 'est_ready_date',
    customRender: ({ text }) => text || '-',
  },
  {
    title: '创建时间',
    dataIndex: 'created_at',
    key: 'created_at',
    customRender: ({ text }) => text ? String(text).slice(0, 10) : '-',
  },
]

const filteredFollowSummary = computed(() => {
  const list = bossData.value.follow_summary || []
  const q = followSummarySearch.value.trim()
  if (!q) return list
  return list.filter(r => r.creator_name.includes(q))
})

const followSummaryColumns = [
  {
    title: '客户',
    dataIndex: 'customer_name',
    key: 'customer_name',
    width: 160,
    ellipsis: true,
  },
  { title: '创建人', dataIndex: 'creator_name', key: 'creator_name', width: 90 },
  { title: '跟进内容', dataIndex: 'content', key: 'content', ellipsis: true },
  {
    title: '时间',
    dataIndex: 'created_at',
    key: 'created_at',
    width: 110,
    customRender: ({ text }) => formatDate(text),
  },
]

function openFollowSummaryModal() {
  followSummarySearch.value = ''
  showAllFollowSummary.value = true
}

const dueTodayColumns = [
  { title: '公司名称', dataIndex: 'company_name', key: 'company_name' },
  { title: '国家', dataIndex: 'country', key: 'country', width: 100 },
  { title: '联系人', dataIndex: 'contact_name', key: 'contact_name', width: 100 },
  {
    title: '客户分级',
    dataIndex: 'grade',
    key: 'grade',
    width: 90,
    customRender: ({ text }) => ({ key: '重点', normal: '普通', potential: '潜在' }[text] || text),
  },
  {
    title: '跟进频次',
    dataIndex: 'follow_freq',
    key: 'follow_freq',
    width: 90,
    customRender: ({ text }) => ({ daily: '每日', weekly: '每周', monthly: '每月' }[text] || text),
  },
  { title: '操作', key: 'action', width: 80 },
]

const allOrdersData = computed(() => {
  if (auth.hasRole('boss', 'super_admin')) return bossData.value.active_orders || []
  return salesData.value.active_orders || []
})

function formatDate(str) {
  if (!str) return ''
  return String(str).slice(0, 10)
}

function canRevoke(ann) {
  return auth.user?.id === ann.created_by || auth.hasRole('super_admin')
}

async function loadAnnouncements() {
  try {
    const res = await announcementsApi.list()
    announcements.value = res.data
  } catch {}
}

async function loadDashboard() {
  if (auth.hasRole('boss', 'super_admin')) {
    try {
      const res = await dashboardApi.boss()
      bossData.value = res.data
    } catch {}
  } else if (auth.hasRole('salesperson')) {
    try {
      const res = await dashboardApi.salesperson()
      salesData.value = res.data
    } catch {}
  }
}

async function revokeAnnouncement(id) {
  try {
    await announcementsApi.revoke(id)
    announcements.value = announcements.value.filter(a => a.id !== id)
    message.success('已撤销')
  } catch {
    message.error('撤销失败')
  }
}

async function submitAnnouncement() {
  if (!newContent.value.trim()) {
    message.warning('请输入通知内容')
    return
  }
  publishing.value = true
  try {
    await announcementsApi.create(newContent.value.trim())
    message.success('发布成功')
    newContent.value = ''
    showPublish.value = false
    await loadAnnouncements()
  } catch {
    message.error('发布失败')
  } finally {
    publishing.value = false
  }
}

onMounted(() => {
  loadAnnouncements()
  loadDashboard()
})
</script>

<style scoped>
.announcements {
  margin-bottom: 16px;
}
.ann-item {
  margin-bottom: 8px;
}
.ann-meta {
  margin-left: 12px;
  color: #999;
  font-size: 12px;
}
.publish-row {
  margin-bottom: 16px;
}
.stat-row {
  margin-bottom: 8px;
}
.stat-card {
  cursor: default;
}
.creator-tag {
  margin-left: 8px;
  font-size: 12px;
  color: #888;
}
</style>
