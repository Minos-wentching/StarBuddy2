<template>
  <v-app id="app">
    <!-- 导航栏 - 在 Home 路由隐藏 -->
    <v-app-bar v-if="authStore.isAuthenticated && !isHomeRoute" prominent class="global-app-bar">
      <v-btn icon @click="router.push('/')"><v-icon>mdi-arrow-left</v-icon></v-btn>
      <v-toolbar-title>星伴 StarBuddy</v-toolbar-title>
      <v-spacer></v-spacer>

      <!-- 人格状态指示器 -->
      <v-chip :color="personaColor" class="mr-2">
        <v-icon start :icon="personaIcon"></v-icon>
        {{ personaDisplay }}
      </v-chip>

      <!-- 情绪强度指示器 -->
      <v-progress-circular
        :model-value="emotionIntensity * 100"
        :color="emotionColor"
        size="30"
        width="3"
        class="mr-2"
      >
        {{ Math.round(emotionIntensity * 100) }}
      </v-progress-circular>

      <!-- 用户菜单 -->
      <v-menu>
        <template v-slot:activator="{ props }">
          <v-btn icon v-bind="props">
            <v-icon>mdi-account</v-icon>
          </v-btn>
        </template>
        <v-list>
          <v-list-item>
            <v-list-item-title>{{ authStore.user?.username }}</v-list-item-title>
          </v-list-item>
          <v-divider></v-divider>
          <v-list-item @click="goToProfile">
            <v-list-item-title>个人资料</v-list-item-title>
          </v-list-item>
          <v-list-item @click="logout">
            <v-list-item-title>退出登录</v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>
    </v-app-bar>

    <!-- 主要内容 -->
    <v-main :class="{ 'no-padding': isHomeRoute }" :style="mainBgStyle">
      <router-view />
    </v-main>

    <!-- 全局Snackbar -->
    <v-snackbar v-model="snackbar.show" :color="snackbar.color" :timeout="3000" location="top">
      {{ snackbar.message }}
    </v-snackbar>

    <!-- SSE连接状态 - 在 Home 路由隐藏 (Home 有自己的 HUD) -->
    <v-footer v-if="authStore.isAuthenticated && !isHomeRoute" app class="px-4 global-footer">
      <v-chip
        :color="sseConnected ? 'green' : 'red'"
        size="small"
      >
        <v-icon start :icon="sseConnected ? 'mdi-wifi' : 'mdi-wifi-off'"></v-icon>
        {{ sseConnected ? '实时连接' : '连接断开' }}
      </v-chip>
      <v-spacer></v-spacer>
      <span class="text-caption">星伴 StarBuddy v1.0.0</span>
    </v-footer>

    <!-- 全局加载状态 -->
    <v-overlay
      :model-value="globalLoading"
      class="align-center justify-center"
      persistent
    >
      <v-progress-circular
        color="primary"
        indeterminate
        size="64"
      ></v-progress-circular>
    </v-overlay>

    <!-- Global quick access + guide -->
    <FloatingDock />
    <GuideBubble />
    <CouncilFlashOverlay />
  </v-app>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { usePersonaStore } from '@/stores/persona'
import { useSSE } from '@/composables/useSSE'
import FloatingDock from '@/components/FloatingDock.vue'
import GuideBubble from '@/components/GuideBubble.vue'
import CouncilFlashOverlay from '@/components/CouncilFlashOverlay.vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const personaStore = usePersonaStore()

const globalLoading = ref(false)

// Check if current route is Home (immersive mode)
const isHomeRoute = computed(() => route.path === '/' || route.name === 'Home')

// Snackbar
const snackbar = ref({
  show: false,
  message: '',
  color: 'info'
})

const showSnackbar = (msg, type = 'info') => {
  snackbar.value.message = msg
  snackbar.value.color = type
  snackbar.value.show = true

  setTimeout(() => {
    snackbar.value.show = false
  }, 3000)
}

// 暴露给全局
window.$snackbar = showSnackbar

// 计算属性
const personaDisplay = computed(() => {
  const personaNames = {
    manager: '安全岛',
    exiles: '感知精灵',
    firefighters: '规则守卫',
    counselor: '星星向导'
  }
  return personaNames[personaStore.currentPersona] || personaStore.currentPersona
})

const personaIcon = computed(() => {
  const personaIcons = {
    manager: 'mdi-island',
    exiles: 'mdi-creation',
    firefighters: 'mdi-shield-star',
    counselor: 'mdi-star-shooting'
  }
  return personaIcons[personaStore.currentPersona] || 'mdi-account'
})

const personaColor = computed(() => personaStore.backgroundColor)
const emotionIntensity = computed(() => personaStore.emotionIntensity)

// 非Home路由时，根据人格设置背景色
const mainBgStyle = computed(() => {
  if (isHomeRoute.value) return {} // Home has ShaderBackground
  const bg = personaStore.backgroundColor || 'hsl(210, 80%, 50%)'
  // 将人格颜色转为深色背景
  const darkBg = bg.replace(/\d+%\)$/, (m) => {
    const lightness = parseInt(m)
    return Math.max(lightness - 35, 8) + '%)'
  })
  return {
    backgroundColor: darkBg,
    transition: 'background-color 0.8s cubic-bezier(0.4, 0, 0.2, 1)',
    minHeight: '100vh'
  }
})
const emotionColor = computed(() => {
  const intensity = emotionIntensity.value
  if (intensity < 0.3) return 'green'
  if (intensity < 0.7) return 'yellow'
  return 'red'
})

// SSE连接 - 仅在非 Home 路由时使用（Home 有自己的 SSE 实例和 HUD）
const { connected: sseConnected } = useSSE(
  () => {
    if (!authStore.isAuthenticated) return ''
    // Home 路由有自己独立的 SSE 连接，这里跳过避免双重连接
    if (route.path === '/' || route.name === 'Home') return ''
    return authStore.currentSessionId
  }
)

// 生命周期
onMounted(() => {
  // 路由守卫已处理认证状态，这里可以添加其他初始化逻辑
})

// 方法
const goToProfile = () => {
  router.push('/profile')
}

const logout = async () => {
  globalLoading.value = true
  try {
    await authStore.logout()
    router.push('/login')
  } catch (error) {
    console.error('退出登录失败:', error)
  } finally {
    globalLoading.value = false
  }
}
</script>

<style scoped>
/* 人格背景色过渡 */
#app {
  transition: background-color 0.8s cubic-bezier(0.4, 0, 0.2, 1);
}

/* 情绪强度指示器动画 */
.v-progress-circular {
  transition: all 0.3s ease;
}

.global-app-bar {
  background:
    linear-gradient(120deg, rgba(156, 39, 176, 0.38), rgba(103, 58, 183, 0.3)) !important;
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.16);
}

.global-footer {
  background:
    linear-gradient(120deg, rgba(80, 34, 108, 0.6), rgba(58, 38, 106, 0.5)) !important;
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  border-top: 1px solid rgba(255, 255, 255, 0.12);
}

.global-app-bar :deep(.v-toolbar-title),
.global-footer :deep(.text-caption) {
  color: rgba(255, 255, 255, 0.88) !important;
}
</style>

<style>
/* Global: remove padding on Home route main */
.v-main.no-padding {
  padding: 0 !important;
}
.v-main.no-padding > .v-main__wrap {
  padding: 0 !important;
}
</style>
