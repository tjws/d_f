import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import CustomerListView from '../views/CustomerListView.vue'
import CustomerDetailView from '../views/CustomerDetailView.vue'
import AdminLayout from '../layouts/AdminLayout.vue'
import AdminUsersView from '../views/admin/AdminUsersView.vue'
import AdminAuditLogsView from '../views/admin/AdminAuditLogsView.vue'
import LoginView from '../views/LoginView.vue'
import { hasAccessToken } from '../composables/useAuth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: LoginView,
    },
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/customers',
      name: 'customers',
      component: CustomerListView,
      meta: { requiresAuth: true },
    },
    {
      path: '/customers/:customerId',
      name: 'customer-detail',
      component: CustomerDetailView,
      meta: { requiresAuth: true },
    },
    {
      path: '/admin',
      component: AdminLayout,
      redirect: '/admin/users',
      meta: { requiresAuth: true },
      children: [
        {
          path: 'users',
          name: 'admin-users',
          component: AdminUsersView,
        },
        {
          path: 'audit-logs',
          name: 'admin-audit-logs',
          component: AdminAuditLogsView,
        },
      ],
    },
  ],
})

router.beforeEach((to) => {
  if (to.meta.requiresAuth && !hasAccessToken()) {
    return {
      name: 'login',
      query: { redirect: to.fullPath },
    }
  }

  if (to.name === 'login' && hasAccessToken()) {
    return { name: 'customers' }
  }

  return true
})

export default router
