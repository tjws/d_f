import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import CustomerListView from '../views/CustomerListView.vue'
import CustomerDetailView from '../views/CustomerDetailView.vue'
import AdminLayout from '../layouts/AdminLayout.vue'
import AdminUsersView from '../views/admin/AdminUsersView.vue'
import AdminAuditLogsView from '../views/admin/AdminAuditLogsView.vue'
import AIDashboardView from '../views/admin/AIDashboardView.vue'
import BusinessDashboardView from '../views/admin/BusinessDashboardView.vue'
import AIWorkflowRunsView from '../views/admin/AIWorkflowRunsView.vue'
import SidebarView from '../views/SidebarView.vue'
import SystemSettingsView from '../views/admin/SystemSettingsView.vue'
import SystemStatusView from '../views/admin/SystemStatusView.vue'
import SalesScriptsView from '../views/admin/SalesScriptsView.vue'
import KnowledgeBaseView from '../views/admin/KnowledgeBaseView.vue'
import RAGEvaluationView from '../views/admin/RAGEvaluationView.vue'
import AIRolloutView from '../views/admin/AIRolloutView.vue'
import AdminOverviewView from '../views/admin/AdminOverviewView.vue'
import AdminTagsView from '../views/admin/AdminTagsView.vue'
import AdminOperationsView from '../views/admin/AdminOperationsView.vue'
import AdminPermissionsView from '../views/admin/AdminPermissionsView.vue'
import AdminDataExportView from '../views/admin/AdminDataExportView.vue'
import LoginView from '../views/LoginView.vue'
import PendingActionsView from '../views/PendingActionsView.vue'
import MyWorkView from '../views/MyWorkView.vue'
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
      path: '/sidebar',
      name: 'sidebar',
      component: SidebarView,
      meta: { requiresAuth: true },
    },
    {
      path: '/pending-actions',
      name: 'pending-actions',
      component: PendingActionsView,
      meta: { requiresAuth: true },
    },
    {
      path: '/my-work',
      name: 'my-work',
      component: MyWorkView,
      meta: { requiresAuth: true },
    },
    {
      path: '/admin',
      component: AdminLayout,
      redirect: '/admin/overview',
      meta: { requiresAuth: true },
      children: [
        {
          path: 'overview',
          name: 'admin-overview',
          component: AdminOverviewView,
        },
        {
          path: 'tags',
          name: 'admin-tags',
          component: AdminTagsView,
        },
        {
          path: 'operations',
          name: 'admin-operations',
          component: AdminOperationsView,
        },
        {
          path: 'permissions',
          name: 'admin-permissions',
          component: AdminPermissionsView,
        },
        {
          path: 'data-export',
          name: 'admin-data-export',
          component: AdminDataExportView,
        },
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
        {
          path: 'ai-dashboard',
          name: 'admin-ai-dashboard',
          component: AIDashboardView,
        },
        {
          path: 'business-dashboard',
          name: 'admin-business-dashboard',
          component: BusinessDashboardView,
        },
        {
          path: 'ai-workflow-runs',
          name: 'admin-ai-workflow-runs',
          component: AIWorkflowRunsView,
        },
        {
          path: 'system-settings',
          name: 'admin-system-settings',
          component: SystemSettingsView,
        },
        {
          path: 'system-status',
          name: 'admin-system-status',
          component: SystemStatusView,
        },
        {
          path: 'sales-scripts',
          name: 'admin-sales-scripts',
          component: SalesScriptsView,
        },
        {
          path: 'knowledge',
          name: 'admin-knowledge',
          component: KnowledgeBaseView,
        },
        {
          path: 'rag-evaluation',
          name: 'admin-rag-evaluation',
          component: RAGEvaluationView,
        },
        {
          path: 'ai-rollout',
          name: 'admin-ai-rollout',
          component: AIRolloutView,
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
