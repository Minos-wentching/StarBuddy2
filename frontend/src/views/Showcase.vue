<template>
  <div class="showcase-root">
    <div class="ambient-layer">
      <div class="orb orb-a"></div>
      <div class="orb orb-b"></div>
      <div class="orb orb-c"></div>
    </div>

    <div class="showcase-shell">
	      <header class="showcase-header">
	        <div class="brand-pill">Hackathon Showcase</div>
	        <v-btn variant="text" size="small" class="skip-btn" @click="skipIntro">回到中枢</v-btn>
	      </header>

      <Transition name="slide-fade" mode="out-in">
        <section :key="currentSlide.id" class="slide-card">
          <div class="slide-index">0{{ currentIndex + 1 }} / 0{{ slides.length }}</div>
          <h1 class="slide-title">{{ currentSlide.title }}</h1>
          <p class="slide-subtitle">{{ currentSlide.subtitle }}</p>

          <ul class="slide-points">
            <li v-for="point in currentSlide.points" :key="point">{{ point }}</li>
          </ul>

	          <div v-if="currentSlide.id === 'scripts'" class="script-grid">
	            <div
	              v-for="script in scripts"
	              :key="script.id"
	              class="script-card"
	              :class="{ selected: selectedScriptId === script.id }"
	              @click="selectedScriptId = script.id"
            >
              <div class="script-title">{{ script.title }}</div>
              <div class="script-theme">{{ script.theme }}</div>
              <div class="script-duration">约 {{ script.durationSec }} 秒</div>
              <v-btn
                size="x-small"
                variant="tonal"
                color="white"
                class="mt-3 text-none"
                @click.stop="quickApplyAndSubmit(script)"
              >
                一键填充并提交
              </v-btn>
            </div>
          </div>

          <div v-if="currentSlide.id === 'scripts'" class="qa-panel">
            <div class="qa-label">简答题（可手填，也可用预制线路一键填充）</div>
            <v-textarea
              v-model="qa.question_1"
              label="1. 最近一次感官不舒服或情绪波动是什么？"
              variant="outlined"
              density="compact"
              rows="2"
              auto-grow
              hide-details
              class="qa-input"
            />
            <v-textarea
              v-model="qa.question_2"
              label="2. 感到不安时，你最常做的事情或想到的念头是什么？"
              variant="outlined"
              density="compact"
              rows="2"
              auto-grow
              hide-details
              class="qa-input"
            />
            <div class="qa-actions">
              <v-btn variant="text" class="nav-btn" @click="clearAnswers">清空</v-btn>
	              <v-btn variant="flat" class="nav-btn primary" @click="submitFromSlide">
	                应用并回到中枢
	              </v-btn>
            </div>
          </div>
        </section>
      </Transition>

      <footer class="showcase-footer">
        <div class="dot-track">
          <span
            v-for="(slide, idx) in slides"
            :key="slide.id"
            class="dot"
            :class="{ active: idx === currentIndex }"
          ></span>
        </div>

        <div class="actions">
          <v-btn variant="text" class="nav-btn" :disabled="currentIndex === 0" @click="prevSlide">上一步</v-btn>
          <v-btn
            v-if="!isLastSlide"
            variant="tonal"
            class="nav-btn primary"
            @click="nextSlide"
          >下一步</v-btn>
	          <v-btn
	            v-else
	            variant="flat"
	            class="nav-btn primary"
	            @click="submitFromSlide"
	          >应用并回到中枢</v-btn>
	        </div>
	      </footer>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { demoScripts } from '@/constants/demoScripts'

const router = useRouter()
const authStore = useAuthStore()

const scripts = demoScripts
const LAST_SCRIPT_KEY_PREFIX = 'starbuddy_last_script_u'
const LAST_ONBOARDING_ANSWERS_KEY_PREFIX = 'starbuddy_last_onboarding_answers_u'

function notify(message, type = 'info') {
  if (typeof window !== 'undefined' && typeof window.$snackbar === 'function') {
    window.$snackbar(message, type)
  }
}

const slides = [
  {
    id: 'vision',
    title: '你的感受不是故障，而是独特的信号',
    subtitle: '星伴陪你理解自己的感知方式，让"不一样"变成"可对话"。',
    points: ['认识你的感知精灵和规则守卫', '实时情绪与感官状态追踪', '会话级成长快照与回溯'],
  },
  {
    id: 'engine',
    title: '在安全岛的陪伴下，探索你的内心世界',
    subtitle: '跟着对话，了解你的感知精灵和规则守卫是如何互动的',
    points: ['SSE 实时事件流', '星球会议多轮协商', '日记图文联动输出'],
  },
  {
    id: 'impact',
    title: '可理解、有共鸣的成长系统',
    subtitle: '捡起漂流瓶，让其他星际伙伴的声音和你产生连接',
    points: [ '可追踪：每次变化有轨迹', '可复用：可扩展多剧本演示'],
  },
  {
    id: 'scripts',
    title: '选一条线路，拿到输入建议',
    subtitle: '你可以手填两句，也可以一键填充；我们会把建议话术放到对话框的输入建议里。',
    points: ['推荐：感官过载线', '日程变化线', '社交困惑线'],
  },
]

const currentIndex = ref(0)
const selectedScriptId = ref(scripts[0]?.id || '')
const qa = ref({
  question_1: '',
  question_2: '',
})

const currentSlide = computed(() => slides[currentIndex.value])
const isLastSlide = computed(() => currentIndex.value === slides.length - 1)

function nextSlide() {
  if (currentIndex.value < slides.length - 1) currentIndex.value += 1
}

function prevSlide() {
  if (currentIndex.value > 0) currentIndex.value -= 1
}

function skipIntro() {
  router.replace('/')
}

function clearAnswers() {
  qa.value = {
    question_1: '',
    question_2: '',
  }
}

function fillAnswersFromScript(script) {
  if (!script) return
  selectedScriptId.value = script.id
  qa.value = {
    question_1: script.presetAnswers?.question_1 || '',
    question_2: script.presetAnswers?.question_2 || '',
  }
}

function persistLastScript(scriptId) {
  const uid = authStore.userId
  if (!uid) return
  try {
    localStorage.setItem(`${LAST_SCRIPT_KEY_PREFIX}${uid}`, String(scriptId || ''))
  } catch {}
}

function persistLastAnswers(answers) {
  const uid = authStore.userId
  if (!uid) return
  try {
    localStorage.setItem(`${LAST_ONBOARDING_ANSWERS_KEY_PREFIX}${uid}`, JSON.stringify(answers || {}))
  } catch {}
}

async function submitFromSlide(scriptOverride = null) {
  const selectedScript = scriptOverride || scripts.find((item) => item.id === selectedScriptId.value) || scripts[0]
  if (!selectedScript) return

  if (scriptOverride) {
    fillAnswersFromScript(selectedScript)
  }

  const answers = {
    question_1: String(qa.value.question_1 || '').trim() || selectedScript.presetAnswers?.question_1 || '',
    question_2: String(qa.value.question_2 || '').trim() || selectedScript.presetAnswers?.question_2 || '',
  }

  persistLastScript(selectedScript.id)
  persistLastAnswers(answers)

  const shouldOnboard = Boolean(authStore.needsOnboarding)
  if (shouldOnboard) {
    if (!authStore.currentSessionId) {
      await authStore.createDefaultSession()
    }
    try {
      const result = await authStore.submitOnboarding(answers, authStore.currentSessionId)
      if (!result.success) {
        notify(result.error || '问卷提交失败，请稍后重试。', 'error')
        return
      }
      notify('已生成画像与记忆球。', 'success')
    } catch (error) {
      console.warn('问卷提交失败:', error)
      notify('问卷提交失败，请稍后重试。', 'error')
      return
    }
  } else {
    notify('已更新输入建议。', 'success')
  }

  router.replace('/')
}

function quickApplyAndSubmit(script) {
  void submitFromSlide(script)
}

onMounted(async () => {
  if (!authStore.isAuthenticated) {
    router.replace('/login')
    return
  }

  if (!selectedScriptId.value && scripts.length) {
    selectedScriptId.value = scripts[0].id
  }

  const selectedScript = scripts.find((item) => item.id === selectedScriptId.value) || scripts[0]
  if (selectedScript) {
    fillAnswersFromScript(selectedScript)
  }
})
</script>

<style scoped>
.showcase-root {
  position: fixed;
  inset: 0;
  overflow: hidden;
  background:
    radial-gradient(circle at 18% 22%, rgba(255, 185, 105, 0.25), transparent 42%),
    radial-gradient(circle at 82% 18%, rgba(83, 131, 255, 0.22), transparent 40%),
    linear-gradient(140deg, #08111d 10%, #0e1f36 42%, #111827 100%);
}

.ambient-layer {
  position: absolute;
  inset: 0;
  overflow: hidden;
}

.orb {
  position: absolute;
  border-radius: 999px;
  filter: blur(18px);
  opacity: 0.6;
  animation: drift 14s ease-in-out infinite;
}

.orb-a {
  width: 340px;
  height: 340px;
  left: -80px;
  bottom: -90px;
  background: rgba(255, 177, 92, 0.35);
}

.orb-b {
  width: 300px;
  height: 300px;
  right: -70px;
  top: 12%;
  background: rgba(92, 146, 255, 0.33);
  animation-delay: 1.8s;
}

.orb-c {
  width: 220px;
  height: 220px;
  right: 22%;
  bottom: 10%;
  background: rgba(115, 245, 210, 0.16);
  animation-delay: 3.2s;
}

.showcase-shell {
  position: relative;
  z-index: 2;
  max-width: 980px;
  height: 100%;
  margin: 0 auto;
  padding: 24px 24px 28px;
  display: flex;
  flex-direction: column;
}

.showcase-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

.brand-pill {
  display: inline-flex;
  align-items: center;
  padding: 7px 12px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.88);
  font-size: 12px;
  letter-spacing: 0.8px;
  text-transform: uppercase;
}

.skip-btn {
  color: rgba(255, 255, 255, 0.75) !important;
}

.slide-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  border-radius: 24px;
  border: 1px solid rgba(255, 255, 255, 0.17);
  background: linear-gradient(145deg, rgba(255, 255, 255, 0.14), rgba(255, 255, 255, 0.05));
  backdrop-filter: blur(18px);
  padding: 44px;
  box-shadow: 0 18px 60px rgba(0, 0, 0, 0.25);
}

.slide-index {
  font-size: 12px;
  letter-spacing: 1.4px;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.58);
  margin-bottom: 18px;
}

.slide-title {
  font-size: clamp(32px, 5.4vw, 56px);
  line-height: 1.08;
  margin: 0;
  color: #f9fafb;
  letter-spacing: 0.4px;
}

.slide-subtitle {
  margin-top: 16px;
  margin-bottom: 24px;
  font-size: clamp(15px, 2.4vw, 19px);
  line-height: 1.8;
  color: rgba(255, 255, 255, 0.83);
  max-width: 840px;
}

.slide-points {
  margin: 0;
  padding-left: 18px;
  display: grid;
  gap: 10px;
  color: rgba(255, 255, 255, 0.9);
  font-size: 15px;
}

.script-grid {
  margin-top: 26px;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.script-card {
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.06);
  text-align: left;
  padding: 14px 14px 12px;
  color: rgba(255, 255, 255, 0.86);
  transition: all 0.22s ease;
  cursor: pointer;
}

.script-card:hover {
  border-color: rgba(255, 219, 137, 0.55);
  transform: translateY(-1px);
}

.script-card.selected {
  border-color: rgba(255, 212, 112, 0.88);
  background: rgba(255, 212, 112, 0.13);
}

.script-title {
  font-size: 14px;
  font-weight: 700;
  margin-bottom: 6px;
}

.script-theme {
  font-size: 12px;
  line-height: 1.6;
  min-height: 38px;
  color: rgba(255, 255, 255, 0.75);
}

.script-duration {
  margin-top: 8px;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.58);
}

.qa-panel {
  margin-top: 18px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.05);
  padding: 14px;
}

.qa-label {
  color: rgba(255, 255, 255, 0.8);
  font-size: 12px;
  margin-bottom: 10px;
}

.qa-input + .qa-input {
  margin-top: 10px;
}

.qa-actions {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.qa-panel :deep(.v-field__outline) {
  --v-field-border-opacity: 0.24;
}

.qa-panel :deep(.v-label) {
  color: rgba(255, 255, 255, 0.58) !important;
}

.qa-panel :deep(.v-field__input) {
  color: rgba(255, 255, 255, 0.9) !important;
}

.showcase-footer {
  margin-top: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.dot-track {
  display: inline-flex;
  gap: 8px;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.3);
}

.dot.active {
  width: 24px;
  background: rgba(255, 223, 138, 0.95);
}

.actions {
  display: inline-flex;
  gap: 8px;
  position: relative;
  top: -10px;
}

.nav-btn {
  border-radius: 999px;
  color: rgba(255, 255, 255, 0.82) !important;
}

.nav-btn.primary {
  background: linear-gradient(120deg, rgba(255, 213, 127, 0.95), rgba(255, 179, 92, 0.92)) !important;
  color: #1f2937 !important;
  font-weight: 700;
}

.slide-fade-enter-active,
.slide-fade-leave-active {
  transition: all 0.32s ease;
}

.slide-fade-enter-from {
  opacity: 0;
  transform: translateX(20px);
}

.slide-fade-leave-to {
  opacity: 0;
  transform: translateX(-18px);
}

@keyframes drift {
  0% {
    transform: translate3d(0, 0, 0) scale(1);
  }
  50% {
    transform: translate3d(14px, -18px, 0) scale(1.04);
  }
  100% {
    transform: translate3d(0, 0, 0) scale(1);
  }
}

@media (max-width: 900px) {
  .showcase-shell {
    padding: 14px;
  }

  .slide-card {
    padding: 26px 18px;
    border-radius: 18px;
  }

  .script-grid {
    grid-template-columns: 1fr;
  }

  .showcase-footer {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
  }

  .actions {
    justify-content: flex-end;
  }
}
</style>
