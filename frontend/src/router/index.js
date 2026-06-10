import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { public: true },
  },
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue'),
      },
      {
        path: 'customers',
        name: 'Customers',
        component: () => import('@/views/customers/CustomerList.vue'),
      },
      {
        path: 'customers/:id',
        name: 'CustomerDetail',
        component: () => import('@/views/customers/CustomerDetail.vue'),
      },
      {
        path: 'follow-ups',
        name: 'FollowUpList',
        component: () => import('@/views/customers/FollowUpList.vue'),
      },
      {
        path: 'products',
        name: 'Products',
        component: () => import('@/views/products/ProductList.vue'),
      },
      {
        path: 'inquiries',
        name: 'InquiryList',
        component: () => import('@/views/inquiry/InquiryList.vue'),
      },
      {
        path: 'inquiries/:id',
        name: 'InquiryDetail',
        component: () => import('@/views/inquiry/InquiryDetail.vue'),
      },
      {
        path: 'formal-orders',
        name: 'OrderList',
        component: () => import('@/views/inquiry/OrderList.vue'),
      },
      {
        path: 'formal-orders/:id',
        name: 'OrderDetail',
        component: () => import('@/views/inquiry/OrderDetail.vue'),
      },
      {
        path: 'settings/users',
        name: 'UserManagement',
        component: () => import('@/views/settings/UserManagement.vue'),
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// finance 角色只允许访问的路由名单
const FINANCE_ALLOWED = ['Dashboard', 'OrderList', 'OrderDetail']

router.beforeEach(async (to) => {
  const { useAuthStore } = await import('@/stores/auth')
  const auth = useAuthStore()
  // 非公开页面：sessionStorage 无缓存时才向后端验证 Cookie，避免每次跳转都发请求
  if (!to.meta.public && !auth.user) {
    await auth.fetchMe()
  }
  if (!to.meta.public && !auth.user) {
    return { name: 'Login' }
  }
  // 已登录用户访问登录页，重定向到首页
  if (to.meta.public && auth.user) {
    return { name: 'Dashboard' }
  }
  if (auth.user?.role === 'finance' && !FINANCE_ALLOWED.includes(to.name)) {
    return { name: 'Dashboard' }
  }
})

export default router
