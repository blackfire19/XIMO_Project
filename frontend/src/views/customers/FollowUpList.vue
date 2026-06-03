<template>
  <div>
    <div class="page-header">
      <a-typography-title :level="4" style="margin: 0">跟进记录</a-typography-title>
    </div>

    <!-- 搜索栏 -->
    <a-card size="small" style="margin-bottom: 16px">
      <a-row :gutter="12" align="middle">
        <a-col :span="10">
          <a-input
            v-model:value="keyword"
            placeholder="搜索客户名称 / 跟进内容 / 跟进人"
            allow-clear
            @pressEnter="doSearch"
            @change="onKeywordChange"
          >
            <template #prefix><search-outlined /></template>
          </a-input>
        </a-col>
        <a-col :span="4">
          <a-select
            v-model:value="effectiveFilter"
            style="width: 100%"
            @change="doSearch"
          >
            <a-select-option :value="null">全部</a-select-option>
            <a-select-option :value="true">有效</a-select-option>
            <a-select-option :value="false">无效</a-select-option>
          </a-select>
        </a-col>
        <a-col :span="3">
          <a-checkbox v-model:checked="todayFilter" @change="doSearch">仅今日</a-checkbox>
        </a-col>
        <a-col :span="4">
          <a-space>
            <a-button type="primary" @click="doSearch">查询</a-button>
            <a-button @click="resetSearch">重置</a-button>
          </a-space>
        </a-col>
      </a-row>
    </a-card>

    <!-- 列表 -->
    <a-table
      :columns="columns"
      :data-source="records"
      :loading="loading"
      row-key="id"
      :pagination="{
        current: currentPage,
        pageSize: pageSize,
        total: total,
        showTotal: (t) => `共 ${t} 条`,
        onChange: onPageChange,
      }"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'customer_name'">
          <a @click="router.push(`/customers/${record.customer_id}`)">
            {{ record.customer_name }}
          </a>
        </template>

        <template v-else-if="column.key === 'is_effective'">
          <a-tag :color="record.is_effective ? 'success' : 'default'">
            {{ record.is_effective ? '有效' : '无效' }}
          </a-tag>
        </template>

        <template v-else-if="column.key === 'content'">
          <span class="content-cell">{{ record.content }}</span>
        </template>
      </template>
    </a-table>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { SearchOutlined } from '@ant-design/icons-vue'
import { customersApi } from '@/api/customers'

const router = useRouter()
const route = useRoute()

const records = ref([])
const loading = ref(false)
const total = ref(0)
const currentPage = ref(1)
const pageSize = 10
const keyword = ref('')
const effectiveFilter = ref(null)
const todayFilter = ref(false)

const columns = [
  { title: '客户名称', key: 'customer_name', width: 160 },
  { title: '跟进内容', key: 'content', ellipsis: true },
  { title: '类型', key: 'is_effective', width: 80 },
  { title: '跟进人', dataIndex: 'creator_name', key: 'creator_name', width: 100 },
  { title: '时间', dataIndex: 'created_at', key: 'created_at', width: 180 },
]

async function loadData(page = 1) {
  loading.value = true
  try {
    const params = { page, page_size: pageSize }
    if (keyword.value) params.keyword = keyword.value
    if (todayFilter.value) params.today = true
    if (effectiveFilter.value !== null) {
      params.effective = effectiveFilter.value
    }
    const res = await customersApi.listAllFollowUps(params)
    records.value = res.data.items
    total.value = res.data.total
    currentPage.value = res.data.page
  } finally {
    loading.value = false
  }
}

function doSearch() {
  loadData(1)
}

function resetSearch() {
  keyword.value = ''
  effectiveFilter.value = null
  todayFilter.value = false
  loadData(1)
}

function onKeywordChange(e) {
  if (!e.target.value) loadData(1)
}

function onPageChange(page) {
  loadData(page)
}

onMounted(() => {
  // 读取 Dashboard 跳转时携带的 URL 参数
  if (route.query.today === '1') todayFilter.value = true
  if (route.query.effective === '1') effectiveFilter.value = true
  if (route.query.effective === '0') effectiveFilter.value = false
  loadData(1)
})
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.content-cell {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
