import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

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
        path: 'quotations',
        name: 'Quotations',
        component: () => import('@/views/quotations/QuotationList.vue'),
      },
      {
        path: 'quotations/:id',
        name: 'QuotationDetail',
        component: () => import('@/views/quotations/QuotationDetail.vue'),
      },
      {
        path: 'orders',
        name: 'Orders',
        component: () => import('@/views/orders/OrderList.vue'),
      },
      {
        path: 'orders/:id',
        name: 'OrderDetail',
        component: () => import('@/views/orders/OrderDetail.vue'),
      },
      {
        path: 'settings/company',
        name: 'CompanySettings',
        component: () => import('@/views/settings/CompanySettings.vue'),
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

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.token) {
    return { name: 'Login' }
  }
})

export default router
