<template>
  <a-layout style="min-height: 100vh">
    <a-layout-sider v-model:collapsed="collapsed" collapsible class="lux-sider">
      <div class="logo">{{ collapsed ? 'XS' : 'XIMOSteel' }}</div>
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
        <a-sub-menu v-if="!auth.hasRole('finance', 'logistics')" key="customers-group">
          <template #title><team-outlined /><span>客户管理</span></template>
          <a-menu-item key="/customers">客户列表</a-menu-item>
          <a-menu-item key="/follow-ups">跟进记录</a-menu-item>
        </a-sub-menu>
        <a-menu-item v-if="!auth.hasRole('finance', 'logistics')" key="/products">
          <database-outlined />
          <span>产品库</span>
        </a-menu-item>
        <a-menu-item v-if="!auth.hasRole('finance', 'logistics')" key="/inquiries">
          <file-text-outlined />
          <span>询价单</span>
        </a-menu-item>
        <a-menu-item key="/formal-orders">
          <shopping-outlined />
          <span>正式订单</span>
        </a-menu-item>
        <a-sub-menu v-if="auth.hasRole('super_admin')" key="settings">
          <template #title>
            <setting-outlined /><span>系统设置</span>
          </template>
          <a-menu-item key="/settings/users">用户管理</a-menu-item>
        </a-sub-menu>
      </a-menu>
    </a-layout-sider>

    <a-layout>
      <a-layout-header class="header">
        <span class="welcome">{{ auth.user?.full_name }}</span>
        <a-button type="link" @click="auth.logout()">退出登录</a-button>
      </a-layout-header>
      <a-layout-content class="content" :class="{ 'content-glass': useGlassBg }">
        <router-view />
      </a-layout-content>
    </a-layout>
  </a-layout>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
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

// 仅首页看板 + 单据详情（询价单/订单）使用渐变毛玻璃底，其余列表页保持白底
const GLASS_ROUTES = ['Dashboard', 'InquiryDetail', 'OrderDetail', 'CustomerDetail']
const useGlassBg = computed(() => GLASS_ROUTES.includes(route.name))

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
/* ===== 左侧菜单：金/黑奢华主题 + 毛玻璃 ===== */
.lux-sider {
  position: relative;
  /* 顶层：45° 极淡拉丝钢板纹路；中层：暖金光晕；底层：近黑金渐变 */
  background:
    repeating-linear-gradient(
      135deg,
      rgba(255, 255, 255, 0.018) 0 1px,
      transparent 1px 20px
    ),
    radial-gradient(95% 55% at 50% -8%, rgba(150, 112, 52, 0.34), transparent 62%),
    linear-gradient(168deg, #0b0a07 0%, #14110a 52%, #0d0b07 100%) !important;
  box-shadow: 1px 0 0 rgba(211, 173, 99, 0.14), 8px 0 28px -18px rgba(0, 0, 0, 0.6);
}
/* 右侧金色细描边 */
.lux-sider::after {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  width: 1px;
  height: 100%;
  background: linear-gradient(
    180deg,
    transparent,
    rgba(211, 173, 99, 0.45) 24%,
    rgba(211, 173, 99, 0.18) 76%,
    transparent
  );
  pointer-events: none;
}

.logo {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: 'Noto Serif SC', 'Songti SC', serif;
  font-size: 19px;
  font-weight: 700;
  letter-spacing: 2px;
  color: #d6b16b;
  text-shadow: 0 1px 8px rgba(214, 177, 107, 0.35);
  border-bottom: 1px solid rgba(211, 173, 99, 0.16);
}

/* 菜单整体透明，露出 sider 金黑底 */
.lux-sider :deep(.ant-menu) {
  background: transparent;
  border-inline-end: none;
}
.lux-sider :deep(.ant-menu-sub.ant-menu-inline) {
  background: rgba(0, 0, 0, 0.22);
}

/* 菜单项 / 子菜单标题：基础态 */
.lux-sider :deep(.ant-menu-item),
.lux-sider :deep(.ant-menu-submenu-title) {
  position: relative;
  margin: 4px 10px;
  width: calc(100% - 20px);
  border-radius: 10px;
  color: #b9b09c !important;
  transition: background 0.22s, transform 0.16s, box-shadow 0.22s, color 0.22s;
}
.lux-sider :deep(.ant-menu-item .anticon),
.lux-sider :deep(.ant-menu-submenu-title .anticon) {
  color: #9a8f79;
  transition: color 0.22s;
}

/* 悬浮：毛玻璃 + 凸起 */
.lux-sider :deep(.ant-menu-item:hover),
.lux-sider :deep(.ant-menu-submenu-title:hover) {
  color: #f2ede2 !important;
  background: rgba(211, 173, 99, 0.14);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  border: 1px solid rgba(211, 173, 99, 0.28);
  transform: translateY(-2px);
  box-shadow: 0 8px 18px -8px rgba(0, 0, 0, 0.6),
    inset 0 1px 0 rgba(255, 255, 255, 0.06);
}
.lux-sider :deep(.ant-menu-item:hover .anticon),
.lux-sider :deep(.ant-menu-submenu-title:hover .anticon) {
  color: #d6b16b;
}

/* 选中态：金色高亮 */
.lux-sider :deep(.ant-menu-item-selected) {
  color: #2a2208 !important;
  background: linear-gradient(180deg, #dcbb70, #c9a253) !important;
  box-shadow: 0 8px 20px -8px rgba(201, 162, 83, 0.55),
    inset 0 1px 0 rgba(255, 255, 255, 0.25);
}
.lux-sider :deep(.ant-menu-item-selected .anticon) {
  color: #2a2208 !important;
}
.lux-sider :deep(.ant-menu-item-selected::after) {
  display: none;
}
/* 子菜单展开/选中标题 */
.lux-sider :deep(.ant-menu-submenu-selected > .ant-menu-submenu-title) {
  color: #d6b16b !important;
}
.lux-sider :deep(.ant-menu-submenu-selected > .ant-menu-submenu-title .anticon) {
  color: #d6b16b !important;
}

/* 折叠触发条 */
.lux-sider :deep(.ant-layout-sider-trigger) {
  background: rgba(0, 0, 0, 0.4);
  color: #d6b16b;
  border-top: 1px solid rgba(211, 173, 99, 0.16);
}

.header {
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: 0 24px;
  gap: 16px;
}
.welcome {
  color: #4a443a;
  font-weight: 500;
}
.content {
  margin: 24px;
  padding: 24px;
  background: #fff;
  border-radius: 8px;
  min-height: 360px;
}
/* 首页看板 + 单据详情：渐变底，承托毛玻璃卡片 */
.content-glass {
  background:
    radial-gradient(120% 80% at 0% 0%, rgba(214, 177, 107, 0.12), transparent 58%),
    radial-gradient(120% 90% at 100% 100%, rgba(120, 140, 180, 0.12), transparent 55%),
    linear-gradient(160deg, #f7f4ed 0%, #eef1f6 100%);
}
</style>
