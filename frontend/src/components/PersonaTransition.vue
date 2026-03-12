<template>
  <Teleport to="body">
    <Transition name="persona-overlay">
      <div v-if="visible" class="persona-transition-overlay" :style="overlayStyle">
        <!-- Ripple circle -->
        <div class="ripple-circle" :style="rippleStyle"></div>
        <!-- Persona info -->
        <div class="persona-info">
          <div class="persona-icon-wrap" :style="{ background: iconBg }">
            <v-icon size="48" color="white">{{ icon }}</v-icon>
          </div>
          <div class="persona-name">{{ name }}</div>
          <div class="persona-desc">{{ description }}</div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, watch, computed, onBeforeUnmount } from 'vue'
import { usePersonaStore } from '@/stores/persona'
import { getPersonaDisplay, getPersonaIcon, getPersonaDescription } from '@/composables/usePersona'

const personaStore = usePersonaStore()
const visible = ref(false)
const currentRole = ref('manager')
let hideTimer = null
let lastAnimatedRole = ''
let lastAnimatedAt = 0

const personaColors = {
  manager: { bg: 'rgba(91, 155, 213, 0.92)', ring: '#5B9BD5', icon: 'rgba(91, 155, 213, 0.9)' },
  exiles: { bg: 'rgba(244, 177, 131, 0.92)', ring: '#F4B183', icon: 'rgba(244, 177, 131, 0.9)' },
  firefighters: { bg: 'rgba(169, 209, 142, 0.92)', ring: '#A9D18E', icon: 'rgba(169, 209, 142, 0.9)' },
  counselor: { bg: 'rgba(180, 167, 214, 0.92)', ring: '#B4A7D6', icon: 'rgba(180, 167, 214, 0.9)' },
}

const colors = computed(() => personaColors[currentRole.value] || personaColors.manager)
const name = computed(() => getPersonaDisplay(currentRole.value))
const icon = computed(() => getPersonaIcon(currentRole.value))
const description = computed(() => getPersonaDescription(currentRole.value))
const overlayStyle = computed(() => ({ background: colors.value.bg }))
const rippleStyle = computed(() => ({ borderColor: colors.value.ring }))
const iconBg = computed(() => colors.value.icon)

const playTransition = (role) => {
  const now = Date.now()
  // 防重：短时间内相同人格的重复事件不重复播放
  if (role === lastAnimatedRole && now - lastAnimatedAt < 900) {
    return
  }
  lastAnimatedRole = role
  lastAnimatedAt = now

  currentRole.value = role
  visible.value = false
  requestAnimationFrame(() => {
    visible.value = true
    if (hideTimer) clearTimeout(hideTimer)
    hideTimer = setTimeout(() => {
      visible.value = false
    }, 1800)
  })
}

watch(() => personaStore.currentPersona, (newVal, oldVal) => {
  const shouldAnimate = newVal === 'exiles' || newVal === 'firefighters'
  if (newVal !== oldVal && oldVal && shouldAnimate) {
    playTransition(newVal)
  }
})

onBeforeUnmount(() => {
  if (hideTimer) clearTimeout(hideTimer)
})
</script>

<style scoped>
.persona-transition-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}

.ripple-circle {
  position: absolute;
  width: 0;
  height: 0;
  border-radius: 50%;
  border: 3px solid white;
  opacity: 0.4;
  animation: ripple-expand 1.5s ease-out forwards;
}

@keyframes ripple-expand {
  0% { width: 0; height: 0; opacity: 0.6; }
  100% { width: 200vmax; height: 200vmax; opacity: 0; }
}

.persona-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  animation: info-appear 0.5s ease-out 0.2s both;
}

@keyframes info-appear {
  0% { opacity: 0; transform: scale(0.7) translateY(20px); }
  100% { opacity: 1; transform: scale(1) translateY(0); }
}

.persona-icon-wrap {
  width: 88px;
  height: 88px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0 40px rgba(255,255,255,0.2);
}

.persona-name {
  font-size: 28px;
  font-weight: 700;
  color: white;
  letter-spacing: 4px;
  text-shadow: 0 2px 12px rgba(0,0,0,0.3);
}

.persona-desc {
  font-size: 14px;
  color: rgba(255,255,255,0.8);
  max-width: 300px;
  text-align: center;
  line-height: 1.5;
}

/* Vue transition */
.persona-overlay-enter-active {
  animation: overlay-in 0.4s ease-out;
}
.persona-overlay-leave-active {
  animation: overlay-out 0.5s ease-in;
}

@keyframes overlay-in {
  0% { opacity: 0; }
  100% { opacity: 1; }
}
@keyframes overlay-out {
  0% { opacity: 1; }
  100% { opacity: 0; }
}
</style>
