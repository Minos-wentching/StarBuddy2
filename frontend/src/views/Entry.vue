<template>
  <div class="entry-root">
    <ShaderBackground role="manager" :intensity="0.12" />

    <div class="entry-card glass-panel">
      <div class="entry-title">请选择进入方式</div>
      <div class="entry-subtitle">你将以哪种身份使用星伴？</div>

      <div class="entry-actions">
        <v-btn
          size="large"
          block
          variant="tonal"
          color="white"
          class="text-none entry-btn"
          @click="enterGuardian"
        >
          <v-icon start>mdi-account-supervisor</v-icon>
          监护人端
        </v-btn>

        <v-btn
          size="large"
          block
          variant="flat"
          class="text-none entry-btn patient-btn"
          @click="enterPatient"
        >
          <v-icon start>mdi-account-heart</v-icon>
          用户端
        </v-btn>
      </div>

      <div v-if="appStore.role" class="entry-hint">
        当前选择：{{ appStore.isGuardian ? '监护人端' : appStore.isPatient ? '用户端' : '未选择' }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ShaderBackground from '@/components/ShaderBackground.vue'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const appStore = useAppStore()

const nextPath = computed(() => String(route.query.next || '/'))

function enterGuardian() {
  appStore.setRole('guardian')
  if (authStore.isAuthenticated) {
    router.push(nextPath.value)
    return
  }
  router.push({ path: '/login', query: { next: nextPath.value } })
}

function enterPatient() {
  appStore.setRole('patient')
  router.push('/patient')
}
</script>

<style scoped>
.entry-root {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.glass-panel {
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 18px;
}

.entry-card {
  position: relative;
  z-index: 10;
  width: 100%;
  max-width: 420px;
  padding: 26px 22px;
}

.entry-title {
  font-size: 22px;
  font-weight: 700;
  color: white;
  letter-spacing: 1px;
}

.entry-subtitle {
  margin-top: 6px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.6);
}

.entry-actions {
  margin-top: 18px;
  display: grid;
  gap: 12px;
}

.entry-btn {
  height: 52px;
  font-weight: 700;
  letter-spacing: 2px;
}

.patient-btn {
  background: rgba(0, 0, 0, 0.65) !important;
  color: white !important;
}

.entry-hint {
  margin-top: 14px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
  text-align: center;
}
</style>

