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
            <a-statistic
              title="进行中订单"
              :value="bossData.active_orders?.length ?? 0"
              :value-style="{ color: '#1677ff', cursor: 'pointer' }"
              @click="$router.push('/formal-orders?active=1')"
            />
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
                        {{ fmtCustomer(item.contact_name, item.customer_name) }}
                      </router-link>
                      <span class="creator-tag">{{ item.creator_name }}</span>
                    </template>
                    <template #description>{{ item.content.length > 60 ? item.content.slice(0, 60) + '…' : item.content }}</template>
                  </a-list-item-meta>
                  <template #extra>
                    <a-space>
                      <span style="color:#999;font-size:12px">{{ formatDate(item.created_at) }}</span>
                      <a-button v-if="!dashEvaluatedIds.has(item.id)" size="small" type="primary" ghost @click="openQuickEval(item)">评价</a-button>
                      <span v-else style="color:#bbb;font-size:12px">已评</span>
                    </a-space>
                  </template>
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
              :custom-row="(record) => ({ onClick: () => $router.push(`/formal-orders/${record.id}`) })"
              :row-class-name="() => 'clickable-row'"
            />
          </a-card>
        </a-col>
      </a-row>

      <!-- 各状态订单统计 -->
      <a-card title="各状态订单统计" size="small" style="margin-top: 16px">
        <a-row :gutter="8">
          <a-col v-for="(count, st) in bossData.order_status_counts" :key="st" :span="4">
            <a-statistic
              :title="ORDER_STATUS_LABELS[st] || st"
              :value="count"
              :value-style="{ color: '#1677ff', cursor: 'pointer' }"
              @click="$router.push(`/formal-orders?status=${st}`)"
            />
          </a-col>
        </a-row>
      </a-card>

      <!-- 员工评价趋势（老板/超管视角） -->
      <a-card size="small" style="margin-top: 16px">
        <template #title>
          员工评价趋势
        </template>
        <template #extra>
          <a-radio-group v-model:value="evalPeriod" size="small" @change="loadEvalStats">
            <a-radio-button value="week">近7天</a-radio-button>
            <a-radio-button value="month">近30天</a-radio-button>
          </a-radio-group>
        </template>
        <div v-if="evalStatsEmpty" style="padding: 24px 0; text-align: center; color: #bbb">
          暂无评价数据
        </div>
        <template v-else>
          <!-- 各员工周期平均分 -->
          <div class="eval-avg-row">
            <div v-for="item in evalAvgList" :key="item.subject_name" class="eval-avg-item">
              <span class="eval-avg-name">{{ item.subject_name }}</span>
              <span class="eval-avg-score" :class="scoreClass(item.avg_score)">
                {{ item.avg_score }}
              </span>
              <span class="eval-avg-unit">分</span>
              <span class="eval-avg-count">（{{ item.count }} 次）</span>
            </div>
          </div>
          <div ref="evalChartRef" style="height: 300px" />
        </template>
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
                      <router-link :to="`/customers/${item.id}`">{{ fmtCustomer(item.contact_name, item.company_name) }}</router-link>
                    </template>
                    <template #description>
                      {{ countryLabel(item.country) }} · {{ GRADE_LABELS[item.grade] }} · {{ FREQ_LABELS[item.follow_freq] }}
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

      <!-- 我的评价趋势（员工视角） -->
      <a-card size="small" style="margin-top: 16px">
        <template #title>我的评价趋势</template>
        <template #extra>
          <a-radio-group v-model:value="evalPeriod" size="small" @change="loadEvalStats">
            <a-radio-button value="week">近7天</a-radio-button>
            <a-radio-button value="month">近30天</a-radio-button>
          </a-radio-group>
        </template>
        <div v-if="evalStatsEmpty" style="padding: 24px 0; text-align: center; color: #bbb">
          暂无评价数据
        </div>
        <template v-else>
          <div class="eval-avg-row">
            <div v-for="item in evalAvgList" :key="item.subject_name" class="eval-avg-item">
              <span class="eval-avg-name">{{ item.subject_name }}</span>
              <span class="eval-avg-score" :class="scoreClass(item.avg_score)">
                {{ item.avg_score }}
              </span>
              <span class="eval-avg-unit">分</span>
              <span class="eval-avg-count">（{{ item.count }} 次）</span>
            </div>
          </div>
          <div ref="evalChartRef" style="height: 260px" />
        </template>
      </a-card>
    </template>

    <!-- ====== 财务看板 ====== -->
    <template v-else-if="auth.hasRole('finance')">
      <a-row :gutter="16" class="stat-row">
        <a-col :span="8">
          <a-card class="stat-card">
            <a-statistic
              title="待记账订单"
              :value="financeData.pending_accounting_count ?? 0"
              :value-style="{ color: '#fa8c16', cursor: 'pointer' }"
              @click="$router.push('/formal-orders?has_accounting=false')"
            />
          </a-card>
        </a-col>
        <a-col :span="8">
          <a-card class="stat-card">
            <a-statistic
              title="已记账订单"
              :value="financeData.accounted_count ?? 0"
              :value-style="{ color: '#52c41a', cursor: 'pointer' }"
              @click="$router.push('/formal-orders?has_accounting=true')"
            />
          </a-card>
        </a-col>
        <a-col :span="8">
          <a-card class="stat-card">
            <a-statistic
              title="待发放工资"
              :value="financeData.salary_pending_count ?? 0"
              :value-style="{ color: '#1677ff', cursor: 'pointer' }"
              @click="$router.push('/formal-orders?has_accounting=true&salary_calculated=false')"
            />
          </a-card>
        </a-col>
      </a-row>

      <a-row :gutter="16" style="margin-top: 16px">
        <a-col :span="12">
          <a-card size="small">
            <template #title>待记账订单</template>
            <template #extra>
              <a-button type="link" size="small" @click="$router.push('/formal-orders?has_accounting=false')">查看全部</a-button>
            </template>
            <a-empty v-if="!financeData.pending_orders?.length" description="暂无待记账订单" />
            <a-table
              v-else
              :data-source="financeData.pending_orders"
              :columns="financeOrderColumns"
              :pagination="false"
              size="small"
              row-key="id"
              :custom-row="(record) => ({ onClick: () => $router.push(`/formal-orders/${record.id}`) })"
              :row-class-name="() => 'clickable-row'"
            />
          </a-card>
        </a-col>
        <a-col :span="12">
          <a-card size="small">
            <template #title>待发放工资订单</template>
            <template #extra>
              <a-button type="link" size="small" @click="$router.push('/formal-orders?has_accounting=true&salary_calculated=false')">查看全部</a-button>
            </template>
            <a-empty v-if="!financeData.salary_pending_orders?.length" description="暂无待发放工资订单" />
            <a-table
              v-else
              :data-source="financeData.salary_pending_orders"
              :columns="financeSalaryColumns"
              :pagination="false"
              size="small"
              row-key="id"
              :custom-row="(record) => ({ onClick: () => $router.push(`/formal-orders/${record.id}`) })"
              :row-class-name="() => 'clickable-row'"
            />
          </a-card>
        </a-col>
      </a-row>
    </template>

    <!-- 采购员看板（仅公告） -->
    <template v-else-if="auth.hasRole('purchaser')">
      <a-empty description="采购员暂无看板数据" style="margin-top: 48px" />
    </template>

    <!-- 后勤看板（仅公告） -->
    <template v-else-if="auth.hasRole('logistics')">
      <a-empty description="后勤暂无看板数据，请前往「正式订单」查看跟单进度" style="margin-top: 48px" />
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
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'action'">
            <a-button v-if="!dashEvaluatedIds.has(record.id)" size="small" type="primary" ghost @click="openQuickEval(record)">评价</a-button>
            <span v-else style="color:#bbb;font-size:12px">已评</span>
          </template>
        </template>
      </a-table>
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
        :pagination="{ pageSize: 10, showTotal: t => `共 ${t} 条` }"
        size="small"
        row-key="id"
        :custom-row="(record) => ({ onClick: () => { $router.push(`/formal-orders/${record.id}`); showAllOrders = false } })"
        :row-class-name="() => 'clickable-row'"
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
              {{ fmtCustomer(record.contact_name, record.company_name) }}
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

    <!-- ====== 弹窗：快捷评价 ====== -->
    <a-modal
      v-model:open="quickEvalVisible"
      :title="`评价 ${quickEvalTarget?.creator_name ?? ''}`"
      :confirm-loading="quickEvalSubmitting"
      ok-text="提交评价"
      cancel-text="取消"
      @ok="submitQuickEval"
      width="400px"
    >
      <a-form layout="vertical" style="margin-top: 8px">
        <a-form-item label="评分（1-10分）" required>
          <a-input-number
            v-model:value="quickEvalForm.score"
            :min="1"
            :max="10"
            :precision="0"
            style="width: 120px"
            placeholder="1-10"
          />
          <span style="margin-left: 8px; color: #999; font-size: 13px">/ 10 分</span>
        </a-form-item>
        <a-form-item label="评语（选填）">
          <a-textarea
            v-model:value="quickEvalForm.comment"
            :rows="3"
            placeholder="输入评语..."
            :maxlength="200"
            show-count
          />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { message } from 'ant-design-vue'
import { NotificationOutlined } from '@ant-design/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { dashboardApi } from '@/api/dashboard'
import { announcementsApi } from '@/api/announcements'
import { evaluationsApi } from '@/api/evaluations'
import * as echarts from 'echarts'
import { fmtCustomer } from '@/utils/format'
import { countryLabel } from '@/utils/countries'

const auth = useAuthStore()

const announcements = ref([])
const bossData = ref({})
const salesData = ref({})
const financeData = ref({})

const showPublish = ref(false)
const newContent = ref('')
const publishing = ref(false)

const showAllFollowSummary = ref(false)
const showAllOrders = ref(false)
const showAllDueToday = ref(false)
const followSummarySearch = ref('')

// 评价趋势图
const evalPeriod = ref('month')
const evalChartRef = ref(null)
const evalStatsEmpty = ref(true)
const evalAvgList = ref([])   // [{ subject_name, avg_score, count }]
let evalChart = null

const financeOrderColumns = [
  { title: '订单号', dataIndex: 'so_number', key: 'so_number' },
  {
    title: '完结时间',
    dataIndex: 'updated_at',
    key: 'updated_at',
    customRender: ({ text }) => text ? String(text).slice(0, 10) : '-',
  },
]

const financeSalaryColumns = [
  { title: '订单号', dataIndex: 'so_number', key: 'so_number' },
  {
    title: '记账时间',
    dataIndex: 'recorded_at',
    key: 'recorded_at',
    customRender: ({ text }) => text ? String(text).slice(0, 10) : '-',
  },
  {
    title: '利润（CNY）',
    dataIndex: 'profit',
    key: 'profit',
    align: 'right',
    customRender: ({ text }) => text != null ? text.toFixed(2) : '—',
  },
]

const ORDER_STATUS_LABELS = {
  confirmed: '已确认',
  production: '生产中',
  ready: '待出运',
  shipping: '出运中',
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
  ...orderColumns,
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
    key: 'customer_name',
    width: 140,
    ellipsis: true,
    customRender: ({ record }) => fmtCustomer(record.contact_name, record.customer_name),
  },
  { title: '创建人', dataIndex: 'creator_name', key: 'creator_name', width: 80 },
  { title: '跟进内容', dataIndex: 'content', key: 'content', ellipsis: true },
  {
    title: '时间',
    dataIndex: 'created_at',
    key: 'created_at',
    width: 100,
    customRender: ({ text }) => formatDate(text),
  },
  { title: '操作', key: 'action', width: 70 },
]

// 已评价的 followup ID 集合（看板用）
const dashEvaluatedIds = ref(new Set())

async function loadDashEvaluatedIds() {
  try {
    const res = await evaluationsApi.list({ target_type: 'followup' })
    dashEvaluatedIds.value = new Set(res.data.map(e => e.target_id))
  } catch {}
}

// 快捷评价
const quickEvalVisible = ref(false)
const quickEvalTarget = ref(null)   // { id, created_by, creator_name }
const quickEvalForm = ref({ score: null, comment: '' })
const quickEvalSubmitting = ref(false)

function openQuickEval(item) {
  quickEvalTarget.value = item
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
      target_type: 'followup',
      target_id: quickEvalTarget.value.id,
      subject_id: quickEvalTarget.value.created_by,
      score: quickEvalForm.value.score,
      comment: quickEvalForm.value.comment || null,
    })
    message.success(`已对 ${quickEvalTarget.value.creator_name} 提交评价`)
    quickEvalVisible.value = false
    loadEvalStats()
    loadDashEvaluatedIds()
  } catch {
    message.error('提交失败')
  } finally {
    quickEvalSubmitting.value = false
  }
}

function openFollowSummaryModal() {
  followSummarySearch.value = ''
  showAllFollowSummary.value = true
}

const dueTodayColumns = [
  {
    title: '公司名称',
    key: 'company_name',
    customRender: ({ record }) => fmtCustomer(record.contact_name, record.company_name),
  },
  {
    title: '国家',
    dataIndex: 'country',
    key: 'country',
    width: 100,
    customRender: ({ text }) => countryLabel(text),
  },
  { title: '联系人', dataIndex: 'contact_name', key: 'contact_name', width: 100 },
  {
    title: '客户分级',
    dataIndex: 'grade',
    key: 'grade',
    width: 90,
    customRender: ({ text }) => GRADE_LABELS[text] || text,
  },
  {
    title: '跟进频次',
    dataIndex: 'follow_freq',
    key: 'follow_freq',
    width: 90,
    customRender: ({ text }) => FREQ_LABELS[text] || text,
  },
  { title: '操作', key: 'action', width: 80 },
]

const allOrdersData = computed(() => {
  if (auth.hasRole('boss', 'super_admin')) return bossData.value.active_orders || []
  return salesData.value.active_orders || []
})

function scoreClass(score) {
  if (score >= 8) return 'score-high'
  if (score >= 6) return 'score-mid'
  return 'score-low'
}

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
      loadDashEvaluatedIds()
    } catch {}
  } else if (auth.hasRole('salesperson')) {
    try {
      const res = await dashboardApi.salesperson()
      salesData.value = res.data
    } catch {}
  } else if (auth.hasRole('finance')) {
    try {
      const res = await dashboardApi.finance()
      financeData.value = res.data
    } catch {}
  }
}

async function loadEvalStats() {
  try {
    const res = await evaluationsApi.stats(evalPeriod.value)
    const stats = res.data  // EmployeeEvalStats[]
    if (!stats || stats.length === 0) {
      evalStatsEmpty.value = true
      evalAvgList.value = []
      return
    }
    evalStatsEmpty.value = false

    // 计算每个员工在当前周期的总平均分
    evalAvgList.value = stats.map(emp => {
      const totalScore = emp.points.reduce((s, p) => s + p.avg_score * p.count, 0)
      const totalCount = emp.points.reduce((s, p) => s + p.count, 0)
      return {
        subject_name: emp.subject_name,
        avg_score: totalCount > 0 ? Math.round((totalScore / totalCount) * 10) / 10 : 0,
        count: totalCount,
      }
    }).sort((a, b) => b.avg_score - a.avg_score)

    // 收集所有日期并排序
    const allDates = [...new Set(stats.flatMap(s => s.points.map(p => p.date)))].sort()

    const series = stats.map(emp => ({
      name: emp.subject_name,
      type: 'line',
      smooth: true,
      data: allDates.map(d => {
        const pt = emp.points.find(p => p.date === d)
        return pt ? pt.avg_score : null
      }),
      connectNulls: true,
    }))

    await nextTick()
    if (!evalChartRef.value) return
    if (!evalChart) {
      evalChart = echarts.init(evalChartRef.value)
    }
    evalChart.setOption({
      tooltip: { trigger: 'axis', formatter: (params) => {
        let s = params[0].axisValue + '<br/>'
        params.forEach(p => {
          const val = p.value != null ? `<b>${p.value}</b> 分` : '<span style="color:#bbb">无记录</span>'
          s += `${p.marker}${p.seriesName}: ${val}<br/>`
        })
        return s
      }},
      legend: { top: 0 },
      grid: { top: 40, bottom: 24, left: 40, right: 20, containLabel: true },
      xAxis: { type: 'category', data: allDates, boundaryGap: false },
      yAxis: { type: 'value', min: 0, max: 10, interval: 2, name: '分' },
      series,
    }, true)
  } catch {}
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
  if (auth.hasRole('boss', 'super_admin', 'salesperson')) {
    loadEvalStats()
  }
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
:deep(.clickable-row) {
  cursor: pointer;
}
.eval-avg-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  padding: 12px 4px 8px;
  border-bottom: 1px solid #f0f0f0;
  margin-bottom: 4px;
}
.eval-avg-item {
  display: flex;
  align-items: baseline;
  gap: 3px;
  background: #fafafa;
  border: 1px solid #f0f0f0;
  border-radius: 6px;
  padding: 6px 12px;
}
.eval-avg-name {
  font-size: 13px;
  color: #555;
  margin-right: 4px;
}
.eval-avg-score {
  font-size: 22px;
  font-weight: 700;
  line-height: 1;
}
.score-high { color: #52c41a; }
.score-mid  { color: #1677ff; }
.score-low  { color: #ff4d4f; }
.eval-avg-unit {
  font-size: 12px;
  color: #999;
}
.eval-avg-count {
  font-size: 12px;
  color: #bbb;
  margin-left: 2px;
}
</style>
