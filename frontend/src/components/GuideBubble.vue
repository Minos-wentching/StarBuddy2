<template>
  <div v-if="!suppressed" class="guide-root" :style="guideStyle">
    <button
      v-if="effectiveMinimized"
      class="guide-min"
      type="button"
      @click="expand"
      aria-label="打开向导"
    >
      <span class="guide-min-ring"></span>
      <v-icon size="20" color="white">mdi-feather</v-icon>
    </button>

    <Transition name="guide-fade">
      <div v-if="!effectiveMinimized && guideState" class="guide-card glass">
        <div class="guide-top">
          <div class="guide-kicker">一张纸条</div>
          <div class="guide-top-actions">
            <button class="guide-top-btn" type="button" @click="minimize" aria-label="最小化">
              <v-icon size="18" color="rgba(255,255,255,0.8)">mdi-minus</v-icon>
            </button>
            <button class="guide-top-btn" type="button" @click="hideForAWhile" aria-label="暂时关闭">
              <v-icon size="18" color="rgba(255,255,255,0.8)">mdi-close</v-icon>
            </button>
          </div>
        </div>

        <div class="guide-text vn-serif">{{ guideState.text }}</div>

        <div class="guide-actions">
          <button class="guide-btn primary" type="button" @click="guideState.primary.onClick">
            {{ guideState.primary.label }}
          </button>
          <button
            v-if="guideState.secondary"
            class="guide-btn"
            type="button"
            @click="guideState.secondary.onClick"
          >
            {{ guideState.secondary.label }}
          </button>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const HIDE_UNTIL_KEY = 'starbuddy_guide_hidden_until'
const MINIMIZED_KEY = 'starbuddy_guide_minimized_v1'

function readNumber(key) {
  try {
    const raw = localStorage.getItem(key)
    const num = Number(raw)
    return Number.isFinite(num) ? num : 0
  } catch {
    return 0
  }
}

function writeNumber(key, value) {
  try {
    localStorage.setItem(key, String(value))
  } catch {}
}

const hiddenUntil = ref(readNumber(HIDE_UNTIL_KEY))
const minimized = ref(readNumber(MINIMIZED_KEY) === 1)

const nowMs = () => Date.now()

// Keep time-based suppression reactive while the app stays open.
const tick = ref(0)
let tickTimer = null
onMounted(() => {
  tickTimer = setInterval(() => {
    tick.value += 1
  }, 15000)
})
onBeforeUnmount(() => {
  if (tickTimer) clearInterval(tickTimer)
})

const suppressed = computed(() => {
  void tick.value
  if (authStore.isAuthenticated && !authStore.needsOnboarding) return true
  return nowMs() < hiddenUntil.value
})

const isHomeRoute = computed(() => route.path === '/' || route.name === 'Home')
const isLoginRoute = computed(() => route.name === 'Login')
const isShowcaseRoute = computed(() => route.name === 'Showcase')

const guideStyle = computed(() => ({
  bottom: isHomeRoute.value
    ? 'calc(180px + env(safe-area-inset-bottom))'
    : 'calc(96px + env(safe-area-inset-bottom))',
}))

function minimize() {
  minimized.value = true
  writeNumber(MINIMIZED_KEY, 1)
}

function expand() {
  minimized.value = false
  writeNumber(MINIMIZED_KEY, 0)
}

function hideForAWhile() {
  // Hide for 45 minutes to avoid annoyance.
  const until = nowMs() + 45 * 60 * 1000
  hiddenUntil.value = until
  writeNumber(HIDE_UNTIL_KEY, until)
}

function focusLoginInput() {
  window.dispatchEvent(new CustomEvent('starbuddy:login-focus'))
}

const guideState = computed(() => {
  if (!authStore.isAuthenticated) {
    if (isLoginRoute.value) {
      return {
        id: 'login',
        text: '写下名字，然后按下那颗“进入”。',
        primary: { label: '聚焦输入框', onClick: focusLoginInput },
        secondary: { label: '我知道了', onClick: hideForAWhile },
      }
    }
    return {
      id: 'need_login',
      text: '给自己起个名字。今晚，我们从一颗记忆开始。',
      primary: {
        label: '去登录',
        onClick: () => router.push({ path: '/login', query: { next: route.fullPath } }),
      },
    }
  }

  if (!authStore.needsOnboarding) return null

  if (isShowcaseRoute.value) {
    return {
      id: 'showcase',
      text: '选一条线路，我们会把建议话术放进输入框上方的“输入建议”。',
      primary: {
        label: '回到中枢',
        onClick: () => router.replace('/'),
      },
      secondary: { label: '我知道了', onClick: hideForAWhile },
    }
  }

  if (isHomeRoute.value) {
    return {
      id: 'need_onboarding',
      text: '第一次来这里：先回答两题，我们会生成你的画像与记忆球。你也可以先选一条线路作为输入建议。',
      primary: { label: '选一条线路', onClick: () => router.push('/showcase') },
      secondary: { label: '稍后再说', onClick: hideForAWhile },
    }
  }

  return {
    id: 'need_onboarding_elsewhere',
    text: '还差两句，我们就能生成你的画像与记忆球。',
    primary: { label: '回到中枢', onClick: () => router.push('/') },
    secondary: { label: '我知道了', onClick: hideForAWhile },
  }
})

const effectiveMinimized = computed(() => minimized.value)
</script>

<style scoped>
.guide-root {
  position: fixed;
  right: 16px;
  z-index: 96;
  pointer-events: auto;
}

.guide-card {
  width: min(280px, calc(100vw - 24px));
  padding: 12px 12px 10px;
  border-radius: 18px;
  transform-origin: 100% 100%;
}

.guide-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.guide-kicker {
  font-size: 11px;
  letter-spacing: 1.8px;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.68);
}

.guide-top-actions {
  display: inline-flex;
  gap: 6px;
}

.guide-top-btn {
  width: 28px;
  height: 28px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.06);
  cursor: pointer;
  display: grid;
  place-items: center;
}

.guide-text {
  color: rgba(255, 255, 255, 0.92);
  font-size: 13px;
  line-height: 1.8;
  padding: 2px 2px 6px;
}

.guide-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.guide-btn {
  border: 1px solid rgba(255, 255, 255, 0.18);
  background: rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.9);
  padding: 8px 10px;
  border-radius: 999px;
  cursor: pointer;
  font-size: 12px;
  transition: transform 0.16s ease, background 0.16s ease, border-color 0.16s ease;
}

.guide-btn:hover {
  transform: translateY(-1px);
  background: rgba(255, 255, 255, 0.11);
  border-color: rgba(255, 255, 255, 0.24);
}

.guide-btn.primary {
  background: linear-gradient(120deg, rgba(255, 214, 122, 0.92), rgba(180, 132, 255, 0.9));
  border-color: rgba(255, 255, 255, 0.18);
  color: rgba(20, 20, 24, 0.92);
  font-weight: 700;
}

.guide-min {
  position: relative;
  width: 44px;
  height: 44px;
  border-radius: 999px;
  border: none;
  cursor: pointer;
  display: grid;
  place-items: center;
  background: rgba(15, 20, 30, 0.72);
  border: 1px solid rgba(255, 255, 255, 0.18);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  box-shadow:
    0 10px 30px rgba(0, 0, 0, 0.35),
    inset 0 1px 0 rgba(255, 255, 255, 0.2);
  -webkit-tap-highlight-color: transparent;
}

.guide-min-ring {
  position: absolute;
  inset: -2px;
  border-radius: 999px;
  background: conic-gradient(
    from 180deg,
    rgba(255, 214, 122, 0.9),
    rgba(180, 132, 255, 0.95),
    rgba(120, 235, 214, 0.85),
    rgba(255, 214, 122, 0.9)
  );
  opacity: 0.8;
  filter: blur(0.3px);
  animation: guide-float 3.8s ease-in-out infinite;
}

.guide-fade-enter-active,
.guide-fade-leave-active {
  transition: all 0.2s ease;
}
.guide-fade-enter-from,
.guide-fade-leave-to {
  opacity: 0;
  transform: translateY(8px) scale(0.98);
}

@keyframes guide-float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-2px); }
}

@media (max-width: 767px) {
  .guide-root { right: 12px; }
}
</style>
