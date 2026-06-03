<template>
  <a-layout style="min-height: 100vh">
    <a-layout-sider v-model:collapsed="collapsed" collapsible>
      <div class="logo">{{ collapsed ? 'TF' : 'TradeFlow' }}</div>
      <a-menu
        v-model:selectedKeys="selectedKeys"
        v-model:openKeys="openKeys"
        theme="dark"
        mode="inline"
        @click="onMenuClick"
      >
        <a-menu-item key="/">
          <dashboard-outlined />
          <span>首页看板</span>
        </a-menu-item>
        <a-sub-menu key="customers-group">
          <template #title><team-outlined /><span>客户管理</span></template>
          <a-menu-item key="/customers">客户列表</a-menu-item>
          <a-menu-item key="/follow-ups">跟进记录</a-menu-item>
        </a-sub-menu>
        <a-menu-item key="/products">
          <database-outlined />
          <span>产品库</span>
        </a-menu-item>
        <a-menu-item key="/quotations">
          <file-text-outlined />
          <span>询报价</span>
        </a-menu-item>
        <a-menu-item key="/orders">
          <shopping-outlined />
          <span>订单管理</span>
        </a-menu-item>
        <a-sub-menu v-if="auth.hasRole('super_admin')" key="settings">
          <template #title>
            <setting-outlined /><span>系统设置</span>
          </template>
          <a-menu-item key="/settings/users">用户管理</a-menu-item>
          <a-menu-item key="/settings/company">公司信息</a-menu-item>
        </a-sub-menu>
      </a-menu>
    </a-layout-sider>

    <a-layout>
      <a-layout-header class="header">
        <span class="welcome">{{ auth.user?.full_name }}</span>
        <a-button type="link" @click="auth.logout()">退出登录</a-button>
      </a-layout-header>
      <a-layout-content class="content">
        <router-view />
      </a-layout-content>
    </a-layout>
  </a-layout>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import {
  DashboardOutlined, TeamOutlined, DatabaseOutlined,
  FileTextOutlined, ShoppingOutlined, SettingOutlined,
} from '@ant-design/icons-vue'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const collapsed = ref(false)
const selectedKeys = ref([route.path])
const openKeys = ref(getOpenKeys(route.path))

function getOpenKeys(path) {
  if (path.startsWith('/customers') || path.startsWith('/follow-ups')) return ['customers-group']
  if (path.startsWith('/settings')) return ['settings']
  return []
}

watch(() => route.path, (path) => {
  selectedKeys.value = [path]
  openKeys.value = getOpenKeys(path)
})

function onMenuClick({ key }) {
  router.push(key)
}
</script>

<style scoped>
.logo {
  height: 64px;
  color: #fff;
  font-size: 18px;
  font-weight: bold;
  display: flex;
  align-items: center;
  justify-content: center;
}
.header {
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: 0 24px;
  gap: 16px;
}
.content {
  margin: 24px;
  padding: 24px;
  background: #fff;
  border-radius: 8px;
  min-height: 360px;
}
</style>
