import { createRouter, createWebHistory } from 'vue-router'

// 极简风格页面组件
import Login from '../views/LoginMinimal.vue'
import Register from '../views/RegisterMinimal.vue'
import MainLayout from '../views/MainLayoutMinimal.vue'

// 功能页面
import Chat from '../views/pages/ChatPage.vue'
import Dashboard from '../views/pages/DashboardPage.vue'
import Statistics from '../views/pages/StatisticsPage.vue'
import Correlation from '../views/pages/CorrelationPage.vue'
import Clustering from '../views/pages/ClusteringPage.vue'
import TimeSeries from '../views/pages/TimeSeriesPage.vue'
import Funnel from '../views/pages/FunnelPage.vue'
import Features from '../views/pages/FeaturesPage.vue'
import Association from '../views/pages/AssociationPage.vue'
import PCA from '../views/pages/PCAPage.vue'

// 数据管理
import DataList from '../views/pages/DataListPage.vue'
import DataImport from '../views/pages/DataImportPage.vue'

// 知识库
import KnowledgeList from '../views/pages/KnowledgeListPage.vue'
import KnowledgeUpload from '../views/pages/KnowledgeUploadPage.vue'

// 预测
import PredictForm from '../views/pages/PredictPage.vue'

// 管理功能
import UserMgmt from '../views/UserMgmt.vue'
import Logs from '../views/pages/LogsPage.vue'

const routes = [
  // 认证路由
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { requiresAuth: false }
  },
  {
    path: '/register',
    name: 'Register',
    component: Register,
    meta: { requiresAuth: false }
  },
  {
    path: '/init-admin',
    name: 'InitAdmin',
    component: Login,
    meta: { requiresAuth: false }
  },
  {
    path: '/chat',
    name: 'Chat',
    component: Chat,
    meta: { title: '智能对话', requiresAuth: true }
  },

  // 主应用路由
  {
    path: '/',
    component: MainLayout,
    redirect: '/dashboard',
    meta: { requiresAuth: true },
    children: [
      // 仪表盘 - 首页
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: Dashboard,
        meta: { title: '数据概览' }
      },

      // ========== 数据分析模块 ==========

      // 统计分析
      {
        path: 'analysis/statistics',
        name: 'Statistics',
        component: Statistics,
        meta: { title: '统计分析' }
      },

      // 相关性分析
      {
        path: 'analysis/correlation',
        name: 'Correlation',
        component: Correlation,
        meta: { title: '相关性分析' }
      },

      // 客户聚类
      {
        path: 'analysis/clustering',
        name: 'Clustering',
        component: Clustering,
        meta: { title: '客户聚类' }
      },

      // 特征重要性
      {
        path: 'analysis/features',
        name: 'Features',
        component: Features,
        meta: { title: '特征分析' }
      },

      // 关联规则
      {
        path: 'analysis/association',
        name: 'Association',
        component: Association,
        meta: { title: '关联规则' }
      },

      // PCA 降维
      {
        path: 'analysis/pca',
        name: 'PCA',
        component: PCA,
        meta: { title: 'PCA 降维' }
      },

      // 时间序列
      {
        path: 'analysis/timeseries',
        name: 'TimeSeries',
        component: TimeSeries,
        meta: { title: '时间趋势' }
      },

      // 漏斗分析
      {
        path: 'analysis/funnel',
        name: 'Funnel',
        component: Funnel,
        meta: { title: '漏斗分析' }
      },

      // ========== 数据管理 ==========

      // 数据列表
      {
        path: 'data/list',
        name: 'DataList',
        component: DataList,
        meta: { title: '数据列表' }
      },

      // 数据导入
      {
        path: 'data/import',
        name: 'DataImport',
        component: DataImport,
        meta: { title: '数据导入' }
      },

      // ========== 知识库 ==========

      // 知识文档列表
      {
        path: 'knowledge/list',
        name: 'KnowledgeList',
        component: KnowledgeList,
        meta: { requiresAnalyst: true, title: '知识库' }
      },

      // 上传文档
      {
        path: 'knowledge/upload',
        name: 'KnowledgeUpload',
        component: KnowledgeUpload,
        meta: { requiresAnalyst: true, title: '上传文档' }
      },

      // ========== 预测 ==========

      {
        path: 'predict',
        name: 'Predict',
        component: PredictForm,
        meta: { title: '智能预测' }
      },

      // ========== 管理功能 ==========

      // 用户管理
      {
        path: 'admin/users',
        name: 'UserMgmt',
        component: UserMgmt,
        meta: { requiresAdmin: true, title: '用户管理' }
      },

      // 操作日志
      {
        path: 'logs',
        name: 'Logs',
        component: Logs,
        meta: { requiresAdmin: true, title: '操作日志' }
      }
    ]
  },

  // 兼容旧路由
  {
    path: '/analysis',
    redirect: '/analysis/statistics'
  },
  {
    path: '/data',
    redirect: '/data/list'
  },
  {
    path: '/knowledge',
    redirect: '/knowledge/list'
  },

  // 404 页面
  {
    path: '/:pathMatch(.*)*',
    redirect: '/dashboard'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')

  // 未登录跳转到登录页
  if (to.meta.requiresAuth !== false && !token) {
    next('/login')
    return
  }

  // 已登录用户访问登录页跳转到首页
  if ((to.path === '/login' || to.path === '/register') && token) {
    next('/dashboard')
    return
  }

  // 管理员权限检查
  if (to.meta.requiresAdmin) {
    const userStr = localStorage.getItem('user')
    if (userStr) {
      const user = JSON.parse(userStr)
      if (user.role !== 'admin') {
        next('/dashboard')
        return
      }
    }
  }

  // 分析师权限检查
  if (to.meta.requiresAnalyst) {
    const userStr = localStorage.getItem('user')
    if (userStr) {
      const user = JSON.parse(userStr)
      if (user.role !== 'admin' && user.role !== 'analyst') {
        next('/dashboard')
        return
      }
    }
  }

  next()
})

export default router
