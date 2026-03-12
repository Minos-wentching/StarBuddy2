import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Home.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { requiresGuest: true }
  },
  {
    path: '/showcase',
    name: 'Showcase',
    component: () => import('@/views/Showcase.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/council',
    name: 'Council',
    component: () => import('@/views/Council.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/history',
    name: 'History',
    component: () => import('@/views/History.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/history/:id',
    name: 'VersionDetail',
    component: () => import('@/views/VersionDetail.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/analytics',
    name: 'Analytics',
    component: () => import('@/views/Analytics.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/views/Settings.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/immersive',
    name: 'Immersive',
    component: () => import('@/views/Immersive.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/report',
    name: 'Report',
    component: () => import('@/views/Report.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/social',
    name: 'Social',
    component: () => import('@/views/Social.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('@/views/Settings.vue'), // 暂时使用Settings
    meta: { requiresAuth: true }
  },
  // 404页面
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFound.vue'),
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

// 路由守卫
import { useAuthStore } from '@/stores/auth'

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()

  // 检查是否要求认证
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next({ path: '/login', query: { next: to.fullPath } })
    return
  }

  // 检查是否要求未认证（如登录/注册页）
  if (to.meta.requiresGuest && authStore.isAuthenticated) {
    next('/')
    return
  }

  next()
})

export default router
