<template>
  <div class="patient-root" :style="rootStyle">
    <!-- Top small menu -->
    <div class="patient-top">
      <button class="menu-btn" type="button" @click="menuOpen = true">菜单</button>
    </div>

    <!-- Content area -->
    <div class="patient-stage">
      <!-- Prompt -->
      <Transition name="fade" mode="out-in">
        <div :key="promptKey" class="patient-prompt">
          {{ promptText }}
        </div>
      </Transition>

      <!-- Name input (page 1) -->
      <div v-if="mode === 'name'" class="name-wrap">
        <input
          v-model="displayName"
          class="name-input"
          type="text"
          autocomplete="off"
          placeholder="请输入你的名字"
          @keydown.enter.prevent="handleBlack()"
        />
        <div v-if="nameError" class="hint-error">{{ nameError }}</div>
      </div>

      <!-- Breathing (gray button) -->
      <div v-else-if="mode === 'breathing'" class="breathing-wrap">
        <div v-if="breathingDone" class="breathing-done-sub">（你可以按黑色按钮继续）</div>
        <div v-else class="breathing-word" :class="{ animate: breathingActive }">
          {{ breathingWord }}
        </div>
      </div>

      <!-- Encouragement interstitial (10s fade-out) -->
      <div v-else-if="mode === 'encourage'" class="encourage-wrap">
        <div class="encourage-text">{{ encouragementText }}</div>
      </div>

      <!-- Instructions (page 2) -->
      <div v-else class="instruction-wrap">
        <Transition name="fade">
          <div v-if="showContinueHint" class="continue-hint">点击黑色按钮继续</div>
        </Transition>
      </div>
    </div>

    <!-- Dog companion (non-blocking) -->
    <div class="dog-wrap" :class="dogClass" aria-hidden="true">
      <!-- Simple SVG silhouette, color/size controlled by CSS -->
      <svg class="dog" viewBox="0 0 64 64" role="img">
        <path
          d="M18 30c-3 0-6 2-7 5l-2 8c-1 3 1 6 4 6h4v6c0 2 2 4 4 4h4c2 0 4-2 4-4v-6h10v6c0 2 2 4 4 4h4c2 0 4-2 4-4v-7c4-1 7-5 7-9v-8c0-4-3-7-7-7h-8l-6-4c-2-1-5-1-7 0l-5 3h-3z"
        />
        <circle cx="44" cy="28" r="2.2" />
        <path d="M50 26l5-6c1-1 3 0 2 2l-4 6" />
      </svg>
    </div>

    <!-- Fixed bottom buttons (always) -->
    <div class="patient-bottom">
      <button class="btn btn-gray" type="button" @click="handleGray()">深呼吸</button>
      <button class="btn btn-black" type="button" @click="handleBlack()">继续</button>
    </div>

    <!-- Menu overlay -->
    <Transition name="fade">
      <div v-if="menuOpen" class="menu-overlay" @click.self="menuOpen = false">
        <div class="menu-panel">
          <button class="menu-item" type="button" @click="goSafetyIsland">安全岛</button>
          <button class="menu-item" type="button" @click="goPickLetter">拾一封信</button>
          <button class="menu-item subtle" type="button" @click="menuOpen = false">关闭</button>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { patientApi } from '@/api/patient'

const router = useRouter()

const DEFAULT_INSTRUCTIONS = [
  '找到水杯',
  '喝一口水',
  '找到椅子',
  '坐下来',
  '听一首歌',
  '休息',
  '画一幅画',
  '跳一跳'
]

const defaultTheme = () => ({
  baseColor: '#0B1B3A',
  enableTransition: false,
  transitionToColor: null,
  transitionDurationSec: 30
})

const mode = ref('name') // name | breathing | encourage | instructions
const menuOpen = ref(false)
const encouragementText = ref('你真棒')

// Theme / background
const bgColor = ref('#0B1B3A')
const bgTransitionSec = ref(0)
const rootStyle = computed(() => ({
  backgroundColor: bgColor.value,
  transition: bgTransitionSec.value ? `background-color ${bgTransitionSec.value}s linear` : 'none'
}))

// Profile
const displayName = ref('')
const nameError = ref('')

// Instructions
const instructions = ref([...DEFAULT_INSTRUCTIONS])
const instructionIndex = ref(0)
const showContinueHint = ref(false)
let instructionTimer = null
let encourageTimer = null
const pendingInstructionIndex = ref(0)
const blackClickCount = ref(0)

// Breathing
const breathingWord = ref('吸气')
const breathingActive = ref(false)
const breathingDone = ref(false)
let breathingTick = null
let breathingPhaseTick = null
const BREATH_PHASE_MS = 7000
const BREATH_CYCLES = 3
const breathingCycle = ref(0) // 0..3

const promptText = computed(() => {
  if (mode.value === 'name') return '你叫什么名字'
  if (mode.value === 'breathing') return breathingDone.value ? '你感觉就好一点了吗' : '深呼吸'
  if (mode.value === 'encourage') return encouragementText.value || '你真棒'
  return instructions.value[instructionIndex.value] || ''
})
const promptKey = computed(() => `${mode.value}:${instructionIndex.value}:${breathingDone.value ? 'done' : 'run'}`)

function hasToken() {
  return Boolean(localStorage.getItem('access_token'))
}

async function loadProfileAndSettings() {
  // Profile
  try {
    if (hasToken()) {
      const res = await patientApi.getProfile()
      const name = String(res.data?.display_name || '').trim()
      if (name) displayName.value = name
    } else {
      const local = String(localStorage.getItem('patient_profile_local') || '').trim()
      if (local) displayName.value = local
    }
  } catch (e) {
    console.warn('Failed to load patient profile:', e)
  }

  // Settings
  try {
    if (hasToken()) {
      const res = await patientApi.getSettings()
      const list = Array.isArray(res.data?.instructions) ? res.data.instructions : []
      instructions.value = list.length ? list.map((x) => String(x || '').trim()).filter(Boolean) : [...DEFAULT_INSTRUCTIONS]
      applyTheme(res.data?.theme)
      encouragementText.value = String(res.data?.encouragementText || '你真棒').trim() || '你真棒'
    } else {
      const raw = localStorage.getItem('patient_settings_local')
      if (raw) {
        const parsed = JSON.parse(raw)
        const list = Array.isArray(parsed?.instructions) ? parsed.instructions : []
        instructions.value = list.length ? list.map((x) => String(x || '').trim()).filter(Boolean) : [...DEFAULT_INSTRUCTIONS]
        applyTheme(parsed?.theme)
        encouragementText.value = String(parsed?.encouragementText || '你真棒').trim() || '你真棒'
      } else {
        instructions.value = [...DEFAULT_INSTRUCTIONS]
        applyTheme(defaultTheme())
        encouragementText.value = '你真棒'
      }
    }
  } catch (e) {
    console.warn('Failed to load patient settings:', e)
    instructions.value = [...DEFAULT_INSTRUCTIONS]
    applyTheme(defaultTheme())
    encouragementText.value = '你真棒'
  }
}

function applyTheme(rawTheme) {
  const theme = { ...defaultTheme(), ...(rawTheme && typeof rawTheme === 'object' ? rawTheme : {}) }
  const base = String(theme.baseColor || '#0B1B3A')
  const enableTransition = Boolean(theme.enableTransition)
  const target = theme.transitionToColor ? String(theme.transitionToColor).trim() : ''
  const duration = Number(theme.transitionDurationSec || 30)

  bgTransitionSec.value = 0
  bgColor.value = base

  if (enableTransition && target) {
    bgTransitionSec.value = Number.isFinite(duration) && duration > 0 ? duration : 30
    nextTick(() => {
      requestAnimationFrame(() => {
        bgColor.value = target
      })
    })
  }
}

function clearInstructionTimer() {
  if (instructionTimer) {
    clearTimeout(instructionTimer)
    instructionTimer = null
  }
}

function clearEncourageTimer() {
  if (encourageTimer) {
    clearTimeout(encourageTimer)
    encourageTimer = null
  }
}

function startInstructionTimer() {
  clearInstructionTimer()
  showContinueHint.value = false
  instructionTimer = setTimeout(() => {
    showContinueHint.value = true
  }, 20000)
}

function stopBreathingTimers() {
  if (breathingTick) clearInterval(breathingTick)
  if (breathingPhaseTick) clearInterval(breathingPhaseTick)
  breathingTick = null
  breathingPhaseTick = null
}

function startBreathing() {
  stopBreathingTimers()
  breathingDone.value = false
  breathingCycle.value = 0
  breathingWord.value = '吸气'
  breathingActive.value = true

  // Toggle inhale/exhale label every 7s
  breathingPhaseTick = setInterval(() => {
    breathingWord.value = breathingWord.value === '吸气' ? '呼气' : '吸气'
  }, BREATH_PHASE_MS)

  // Each full cycle is 14s; after 3 cycles mark done
  breathingTick = setInterval(() => {
    breathingCycle.value += 1
    if (breathingCycle.value >= BREATH_CYCLES) {
      breathingDone.value = true
      breathingActive.value = false
      stopBreathingTimers()
    }
  }, BREATH_PHASE_MS * 2)
}

function handleGray() {
  mode.value = 'breathing'
  startBreathing()
}

async function saveProfileName(name) {
  const trimmed = String(name || '').trim()
  if (!trimmed) return

  if (hasToken()) {
    await patientApi.updateProfile({ display_name: trimmed })
    return
  }
  localStorage.setItem('patient_profile_local', trimmed)
}

function enterInstructions() {
  mode.value = 'instructions'
  instructionIndex.value = 0
  startInstructionTimer()
}

const dogStage = computed(() => {
  const c = Number(blackClickCount.value || 0)
  if (c > 8) return 3
  if (c > 4) return 2
  if (c > 2) return 1
  return 0
})

const dogClass = computed(() => {
  if (dogStage.value === 3) return 'run big'
  if (dogStage.value === 2) return 'walk big'
  if (dogStage.value === 1) return 'big'
  return 'small'
})

async function incrementBlackClickCount() {
  try {
    if (hasToken()) {
      const res = await patientApi.incrementBlackClick()
      blackClickCount.value = Number(res.data?.blackClickCount || blackClickCount.value || 0)
      return
    }
  } catch (e) {
    console.warn('Failed to increment black click:', e)
  }

  const next = Number(blackClickCount.value || 0) + 1
  blackClickCount.value = next
  localStorage.setItem('patient_black_click_count_local', String(next))
}

function showEncouragementThenNextInstruction(nextIndex) {
  clearInstructionTimer()
  clearEncourageTimer()
  showContinueHint.value = false
  pendingInstructionIndex.value = nextIndex
  mode.value = 'encourage'
  encourageTimer = setTimeout(() => {
    instructionIndex.value = pendingInstructionIndex.value
    mode.value = 'instructions'
    startInstructionTimer()
  }, 10000)
}

async function handleBlack() {
  nameError.value = ''

  if (mode.value === 'name') {
    const trimmed = displayName.value.trim()
    if (!trimmed) {
      nameError.value = '名字不能为空'
      return
    }
    try {
      await saveProfileName(trimmed)
    } catch (e) {
      console.warn('Failed to save profile name:', e)
    }
    enterInstructions()
    return
  }

  if (mode.value === 'breathing') {
    if (!displayName.value.trim()) {
      nameError.value = '请先输入名字'
      mode.value = 'name'
      return
    }
    enterInstructions()
    return
  }

  if (mode.value === 'encourage') return

  // instructions mode: insert 10s encouragement between transitions
  await incrementBlackClickCount()
  const nextIndex = (instructionIndex.value + 1) % Math.max(1, instructions.value.length)
  showEncouragementThenNextInstruction(nextIndex)
}

function goSafetyIsland() {
  menuOpen.value = false
  router.push('/immersive')
}

function goPickLetter() {
  menuOpen.value = false
  router.push('/social?tab=bottle&action=pick')
}

watch(
  () => mode.value,
  (m) => {
    if (m === 'instructions') {
      startInstructionTimer()
      stopBreathingTimers()
      clearEncourageTimer()
      return
    }
    if (m === 'breathing') {
      clearInstructionTimer()
      clearEncourageTimer()
      return
    }
    if (m === 'encourage') {
      clearInstructionTimer()
      stopBreathingTimers()
      return
    }
    // name
    clearInstructionTimer()
    stopBreathingTimers()
    clearEncourageTimer()
  }
)

onMounted(async () => {
  try {
    if (hasToken()) {
      const res = await patientApi.getMetrics()
      blackClickCount.value = Number(res.data?.blackClickCount || 0)
    } else {
      blackClickCount.value = Number(localStorage.getItem('patient_black_click_count_local') || 0)
    }
  } catch (e) {
    console.warn('Failed to load patient metrics:', e)
    blackClickCount.value = Number(localStorage.getItem('patient_black_click_count_local') || 0)
  }
  await loadProfileAndSettings()
})

onBeforeUnmount(() => {
  clearInstructionTimer()
  clearEncourageTimer()
  stopBreathingTimers()
})
</script>

<style scoped>
.patient-root {
  position: fixed;
  inset: 0;
  overflow: hidden;
}

.patient-top {
  position: fixed;
  top: calc(14px + env(safe-area-inset-top));
  right: 14px;
  z-index: 30;
}

.menu-btn {
  border: 1px solid rgba(255, 255, 255, 0.18);
  background: rgba(0, 0, 0, 0.25);
  color: rgba(255, 255, 255, 0.9);
  height: 34px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 12px;
  letter-spacing: 2px;
  cursor: pointer;
}

.patient-stage {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 22px;
  padding-bottom: 120px;
}

.patient-prompt {
  color: white;
  font-size: 48px;
  font-weight: 700;
  letter-spacing: 2px;
  text-align: center;
  max-width: 820px;
  line-height: 1.15;
  transform: translateY(-70px);
  position: relative;
  z-index: 20;
}

.name-wrap {
  margin-top: 18px;
  width: min(520px, 92vw);
  transform: translateY(-42px);
}

.name-input {
  width: 100%;
  height: 52px;
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.22);
  background: rgba(255, 255, 255, 0.06);
  color: white;
  padding: 0 16px;
  font-size: 16px;
  outline: none;
}

.name-input::placeholder {
  color: rgba(255, 255, 255, 0.5);
}

.hint-error {
  margin-top: 10px;
  color: rgba(255, 210, 210, 0.95);
  font-size: 13px;
  text-align: center;
}

.breathing-wrap,
.instruction-wrap,
.encourage-wrap {
  width: 100%;
  display: grid;
  place-items: center;
  transform: translateY(-10px);
}

.breathing-word {
  color: white;
  opacity: 0.9;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 4px;
  transform: translateY(-26px);
}

.breathing-word.animate {
  animation: breathe-size 14s ease-in-out infinite;
}

@keyframes breathe-size {
  0% { font-size: 12px; opacity: 0.85; }
  50% { font-size: 50px; opacity: 0.98; }
  100% { font-size: 12px; opacity: 0.85; }
}

.breathing-done-sub {
  color: rgba(255, 255, 255, 0.65);
  font-size: 14px;
  transform: translateY(-24px);
}

.continue-hint {
  color: white;
  font-size: 32px;
  font-weight: 700;
  letter-spacing: 2px;
  transform: translateY(-10px);
  opacity: 0.92;
}

.encourage-text {
  color: white;
  font-size: 48px;
  font-weight: 700;
  letter-spacing: 2px;
  text-align: center;
  opacity: 1;
  animation: fade-out-10 10s linear forwards;
}
@keyframes fade-out-10 {
  0% { opacity: 1; }
  100% { opacity: 0; }
}

.dog-wrap {
  position: fixed;
  left: 14px;
  bottom: calc(118px + env(safe-area-inset-bottom));
  z-index: 12;
  pointer-events: none;
  opacity: 0.86;
}
.dog {
  display: block;
  width: 48px;
  height: 48px;
  fill: rgba(220, 220, 220, 0.92);
  filter: drop-shadow(0 6px 14px rgba(0, 0, 0, 0.25));
}
.dog-wrap.big .dog {
  width: 68px;
  height: 68px;
}
.dog-wrap.walk {
  animation: dog-walk 0.65s ease-in-out infinite;
}
@keyframes dog-walk {
  0%, 100% { transform: translateX(0) translateY(0); }
  50% { transform: translateX(3px) translateY(-1px); }
}
.dog-wrap.run {
  left: -90px;
  animation: dog-run 2.8s linear infinite;
}
@keyframes dog-run {
  0% { transform: translateX(0); }
  100% { transform: translateX(calc(100vw + 180px)); }
}

.patient-bottom {
  position: fixed;
  left: 50%;
  transform: translateX(-50%);
  bottom: calc(26px + env(safe-area-inset-bottom));
  z-index: 40;
  display: flex;
  gap: 14px;
}

.btn {
  height: 56px;
  min-width: 168px;
  padding: 0 18px;
  border-radius: 16px;
  border: none;
  cursor: pointer;
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 2px;
}

.btn-gray {
  background: rgba(230, 230, 230, 0.92);
  color: rgba(0, 0, 0, 0.78);
}

.btn-black {
  background: rgba(0, 0, 0, 0.86);
  color: white;
}

.menu-overlay {
  position: fixed;
  inset: 0;
  z-index: 60;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: flex-start;
  justify-content: flex-end;
  padding: 64px 14px 14px 14px;
}

.menu-panel {
  width: 160px;
  border-radius: 16px;
  padding: 10px;
  background: rgba(10, 12, 18, 0.72);
  border: 1px solid rgba(255, 255, 255, 0.14);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  display: grid;
  gap: 8px;
}

.menu-item {
  height: 40px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.16);
  background: rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.92);
  font-size: 13px;
  letter-spacing: 2px;
  cursor: pointer;
}

.menu-item.subtle {
  background: transparent;
  color: rgba(255, 255, 255, 0.55);
  border-color: rgba(255, 255, 255, 0.1);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.25s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
