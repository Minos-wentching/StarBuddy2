<template>
  <div v-if="!isHidden" class="dock-root" :style="dockStyle">
    <Transition name="dock-menu">
      <div v-if="open" class="dock-menu glass">
        <button class="dock-item" type="button" @click="goHome">
          <v-icon size="18">mdi-home-variant</v-icon>
          <span>记忆中枢</span>
        </button>
        <button class="dock-item" type="button" @click="goScripts">
          <v-icon size="18">mdi-book-open-variant</v-icon>
          <span>选一条线路</span>
        </button>
        <button class="dock-item" type="button" @click="goReport">
          <v-icon size="18">mdi-map-marker-radius</v-icon>
          <span>看我的星图</span>
        </button>
        <button class="dock-item" type="button" @click="goBottle">
          <v-icon size="18">mdi-bottle-wine</v-icon>
          <span>拾一封信</span>
        </button>
      </div>
    </Transition>

    <button class="dock-orb" :class="{ open }" type="button" @click="toggle">
      <span class="dock-orb-ring"></span>
      <span class="dock-orb-core">
        <v-icon size="22" color="white">{{ open ? 'mdi-close' : 'mdi-compass-outline' }}</v-icon>
      </span>
    </button>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const open = ref(false)

const isHomeRoute = computed(() => route.path === '/' || route.name === 'Home')
const isHidden = computed(() => route.name === 'Showcase') // Showcase is already a guided flow

const dockStyle = computed(() => ({
  bottom: isHomeRoute.value
    ? 'calc(108px + env(safe-area-inset-bottom))'
    : 'calc(22px + env(safe-area-inset-bottom))',
}))

watch(
  () => route.fullPath,
  () => {
    open.value = false
  }
)

function toggle() {
  open.value = !open.value
}

function goRequireAuth(targetPath) {
  open.value = false
  if (authStore.isAuthenticated) {
    router.push(targetPath)
    return
  }
  router.push({ path: '/login', query: { next: String(targetPath) } })
}

function goHome() {
  goRequireAuth('/')
}

function goScripts() {
  goRequireAuth('/showcase')
}

function goReport() {
  goRequireAuth('/report')
}

function goBottle() {
  goRequireAuth('/social?tab=bottle&action=pick')
}
</script>

<style scoped>
.dock-root {
  position: fixed;
  right: 16px;
  z-index: 95;
  pointer-events: auto;
}

.dock-orb {
  position: relative;
  width: 54px;
  height: 54px;
  border: none;
  padding: 0;
  border-radius: 999px;
  background: transparent;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}

.dock-orb-ring {
  position: absolute;
  inset: 0;
  border-radius: 999px;
  background: conic-gradient(
    from 180deg,
    rgba(255, 214, 122, 0.9),
    rgba(180, 132, 255, 0.95),
    rgba(120, 235, 214, 0.85),
    rgba(255, 214, 122, 0.9)
  );
  filter: blur(0.2px);
  opacity: 0.86;
  animation: dock-float 3.4s ease-in-out infinite;
}

.dock-orb-core {
  position: absolute;
  inset: 2px;
  border-radius: 999px;
  display: grid;
  place-items: center;
  background: rgba(15, 20, 30, 0.72);
  border: 1px solid rgba(255, 255, 255, 0.18);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  box-shadow:
    0 10px 30px rgba(0, 0, 0, 0.35),
    inset 0 1px 0 rgba(255, 255, 255, 0.2);
  transition: transform 0.18s ease;
}

.dock-orb.open .dock-orb-core {
  transform: scale(0.98);
}

.dock-menu {
  width: 168px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px;
  margin-bottom: 10px;
  border-radius: 18px;
}

.dock-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  width: 100%;
  border: none;
  border-radius: 14px;
  cursor: pointer;
  color: rgba(255, 255, 255, 0.92);
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.14);
  transition: transform 0.18s ease, background 0.18s ease, border-color 0.18s ease;
  text-align: left;
  font-size: 12px;
}

.dock-item:hover {
  transform: translateY(-1px);
  background: rgba(255, 255, 255, 0.11);
  border-color: rgba(255, 255, 255, 0.22);
}

.dock-item:active {
  transform: translateY(0);
}

.dock-menu-enter-active,
.dock-menu-leave-active {
  transition: all 0.18s ease;
}
.dock-menu-enter-from,
.dock-menu-leave-to {
  opacity: 0;
  transform: translateY(10px) scale(0.98);
}

@keyframes dock-float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-2px); }
}

@media (max-width: 767px) {
  .dock-root { right: 12px; }
  .dock-menu { width: 154px; }
}
</style>
