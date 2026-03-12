<template>
  <div
    class="council-flash-overlay"
    :class="{ active: flashing }"
    aria-hidden="true"
  ></div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { usePersonaStore } from '@/stores/persona'

const personaStore = usePersonaStore()

const flashing = ref(false)
const reduceAnimations = ref(false)

let lastLen = Array.isArray(personaStore.councilRounds)
  ? personaStore.councilRounds.length
  : 0

let flashTimer = null

function readReduceAnimations() {
  try {
    const raw = localStorage.getItem('appSettings')
    if (!raw) return false
    const parsed = JSON.parse(raw)
    return Boolean(parsed?.reduceAnimations)
  } catch {
    return false
  }
}

function prefersReducedMotion() {
  try {
    return window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches === true
  } catch {
    return false
  }
}

function triggerFlash() {
  if (reduceAnimations.value) return
  if (prefersReducedMotion()) return

  // Restart CSS animation reliably.
  flashing.value = false
  requestAnimationFrame(() => {
    flashing.value = true
    if (flashTimer) clearTimeout(flashTimer)
    flashTimer = setTimeout(() => {
      flashing.value = false
    }, 360)
  })
}

function handleAppSettingsChanged(e) {
  try {
    reduceAnimations.value = Boolean(e?.detail?.reduceAnimations)
  } catch {}
}

watch(
  () => (Array.isArray(personaStore.councilRounds) ? personaStore.councilRounds.length : 0),
  (len) => {
    if (len > lastLen) triggerFlash()
    lastLen = len
  }
)

onMounted(() => {
  reduceAnimations.value = readReduceAnimations()
  window.addEventListener('appSettingsChanged', handleAppSettingsChanged)
})

onBeforeUnmount(() => {
  window.removeEventListener('appSettingsChanged', handleAppSettingsChanged)
  if (flashTimer) clearTimeout(flashTimer)
})
</script>

<style scoped>
.council-flash-overlay {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 9999;
  opacity: 0;
  background:
    radial-gradient(circle at 18% 16%, rgba(255, 215, 120, 0.26), transparent 42%),
    radial-gradient(circle at 78% 26%, rgba(120, 190, 255, 0.16), transparent 48%),
    radial-gradient(circle at 50% 50%, rgba(255, 255, 255, 0.05), transparent 58%);
  mix-blend-mode: screen;
}

.council-flash-overlay.active {
  animation: council-flash 360ms ease-out;
}

@keyframes council-flash {
  0% {
    opacity: 0;
  }
  24% {
    opacity: 1;
  }
  100% {
    opacity: 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .council-flash-overlay {
    display: none;
  }
}
</style>

