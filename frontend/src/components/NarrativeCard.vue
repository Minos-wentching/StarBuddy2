<template>
  <div
    ref="card"
    class="glass max-w-[min(72ch,88vw)] w-[min(72ch,88vw)] px-8 py-10 md:px-12 md:py-14 vn-serif shadow-2xl"
    :style="cardStyle"
    @click="$emit('next')"
  >
    <div class="text-[1.125rem] md:text-[1.25rem] text-white/92">
      <p class="whitespace-pre-wrap">{{ displayText }}</p>
    </div>
    <div class="mt-6 flex items-center gap-3 opacity-70">
      <span class="inline-block w-2 h-2 rounded-full" :style="{ background: accentColor }"></span>
      <span class="text-xs uppercase tracking-widest">{{ roleLabel }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, computed } from 'vue'
import { animate, spring } from 'motion'
import { getPersonaOklch } from '@/design-system/colors'

const props = defineProps({
  text: { type: String, default: '' },
  role: { type: String, default: 'manager' },
  speed: { type: Number, default: 22 }, // 每帧字符数
})

defineEmits(['next'])

const card = ref(null)
const displayText = ref('')

const accentColor = computed(() => getPersonaOklch(props.role))
const roleLabel = computed(() => {
  const map = { manager: '安全岛', exiles: '感知精灵', firefighters: '规则守卫', counselor: '星星向导' }
  return map[props.role] || props.role
})

const cardStyle = computed(() => ({
  '--glass-tint': accentColor.value,
  borderRadius: '24px',
  outline: `1px solid color-mix(in oklab, ${accentColor.value} 30%, transparent)`,
  boxShadow:
    `inset 0 1px 0 color-mix(in oklab, white 20%, transparent), 
     0 10px 60px rgba(0,0,0,0.35), 
     0 0 0 1px color-mix(in oklab, ${accentColor.value} 15%, transparent)`,
  textShadow: '0 2px 8px rgba(0,0,0,0.35)',
}))

function typewriter(text) {
  const raw = text.replace(/\r\n/g, '\n')
  let i = 0
  displayText.value = ''

  function step() {
    const chunk = raw.slice(i, i + Math.max(1, Math.floor(props.speed / 2)))
    displayText.value += chunk
    i += chunk.length
    if (i < raw.length) {
      requestAnimationFrame(step)
    }
  }
  requestAnimationFrame(step)
}

watch(() => props.text, (t, prev) => {
  if (card.value) {
    animate(card.value, { opacity: [0, 1], y: [-8, 0] }, { duration: 0.5, easing: 'ease-out' })
  }
  typewriter(t || '')
}, { immediate: true })

onMounted(() => {
  if (card.value) {
    animate(card.value, { opacity: [0, 1], y: [12, 0], filter: ['blur(4px)', 'blur(0px)'] }, { duration: 0.6, easing: spring() })
  }
})
</script>

<style scoped>
.glass {
  color: #f6f6f6;
}
</style>

