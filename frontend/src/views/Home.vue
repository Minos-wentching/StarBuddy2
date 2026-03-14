<template>
  <div class="home-root">
    <!-- Shader Background (always present) -->
    <ShaderBackground
      :role="personaStore.currentPersona"
      :intensity="personaStore.emotionIntensity"
    />

    <!-- Persona Transition Overlay -->
    <PersonaTransition />

    <!-- Council Debate Overlay -->
    <Transition name="council-overlay">
      <div v-if="personaStore.isInnerCouncilActive || showCouncilOverlay" class="council-overlay">
        <div class="council-overlay-inner glass-panel">
          <div class="council-overlay-header">
            <v-icon color="white" size="24" class="mr-2">mdi-account-group</v-icon>
            <span class="text-h6 font-weight-bold" style="color:white">星球会议进行中</span>
            <v-spacer />
            <v-btn icon variant="text" size="small" @click="showCouncilOverlay = false" style="color:rgba(255,255,255,0.7)">
              <v-icon>mdi-close</v-icon>
            </v-btn>
          </div>
          <CouncilDebateLog />
        </div>
      </div>
    </Transition>

    <!-- HUD: Unified Container -->
    <div class="hud-container">
      <!-- Left: Persona Indicator -->
      <div class="hud-interactive d-flex flex-column gap-2">
        <div class="hud-persona glass-chip" @click="showDashboard = !showDashboard">
          <v-avatar :color="getPersonaColor(personaStore.currentPersona)" size="32">
            <v-icon color="white" size="18">{{ getPersonaIcon(personaStore.currentPersona) }}</v-icon>
          </v-avatar>
          <div class="hud-persona-info">
            <div class="hud-persona-name">{{ currentPersonaDisplay }}</div>
            <div class="hud-emotion-bar">
              <div class="hud-emotion-fill" :style="emotionBarStyle"></div>
            </div>
          </div>
          <v-icon size="16" style="color:rgba(255,255,255,0.5)">
            {{ showDashboard ? 'mdi-chevron-up' : 'mdi-chevron-down' }}
          </v-icon>
        </div>

        <!-- SSE connection indicator (hidden for cleaner UX) -->
      </div>

      <!-- Center: Progress Stepper (Absolute centered) -->
      <div class="hud-progress-centered hud-interactive">
        <div class="progress-stepper glass-chip-sm">
          <div v-for="(step, i) in experienceSteps" :key="i"
               class="step-item"
               :class="{ active: i === currentStep, completed: i < currentStep }">
            <div class="step-dot">
              <v-icon v-if="i < currentStep" size="10" color="white">mdi-check</v-icon>
            </div>
            <span class="step-label">{{ step }}</span>
          </div>
        </div>
      </div>

      <!-- Right: Menu -->
      <div class="hud-interactive">
        <v-menu>
          <template v-slot:activator="{ props }">
            <v-btn icon variant="text" v-bind="props" class="hud-btn glass-chip-sm">
              <v-icon color="white">mdi-menu</v-icon>
            </v-btn>
	          </template>
	          <v-list density="compact" class="glass-menu">
	            <v-list-item @click="activePanel = 'album'" prepend-icon="mdi-image-multiple">
	              <v-list-item-title>感知画册</v-list-item-title>
	            </v-list-item>
            <v-list-item @click="showCouncilOverlay = true" prepend-icon="mdi-account-group">
              <v-list-item-title>会议记录</v-list-item-title>
            </v-list-item>
            <v-list-item :to="'/settings'" prepend-icon="mdi-cog">
              <v-list-item-title>更多选项</v-list-item-title>
            </v-list-item>
            <v-list-item :to="'/report'" prepend-icon="mdi-file-document-outline">
              <v-list-item-title>成长报告</v-list-item-title>
            </v-list-item>
            <v-divider />
            <v-list-item @click="handleLogout" prepend-icon="mdi-logout">
              <v-list-item-title>退出</v-list-item-title>
            </v-list-item>
          </v-list>
        </v-menu>
      </div>
    </div>

    <!-- Expandable Dashboard Panel (slides from left) -->
    <Transition name="slide-left">
      <div v-if="showDashboard" class="dashboard-panel glass-panel">
        <div class="pa-4">
          <!-- Current persona detail -->
          <div class="text-center mb-4">
            <v-avatar :color="getPersonaColor(personaStore.currentPersona)" size="56" class="mb-2 elevation-4">
              <v-icon color="white" size="28">{{ getPersonaIcon(personaStore.currentPersona) }}</v-icon>
            </v-avatar>
            <div class="text-h6 font-weight-bold" style="color:white">{{ currentPersonaDisplay }}</div>
            <div class="text-caption" style="color:rgba(255,255,255,0.6)">
              {{ getPersonaDescription(personaStore.currentPersona) }}
            </div>
          </div>

          <!-- Emotion intensity -->
          <div class="mb-4">
            <div class="d-flex justify-space-between text-caption mb-1" style="color:rgba(255,255,255,0.7)">
              <span>情绪强度</span>
              <span>{{ Math.round(personaStore.emotionIntensity * 100) }}%</span>
            </div>
            <v-progress-linear
              :model-value="personaStore.emotionIntensity * 100"
              :color="emotionBarColor"
              height="8" rounded
              bg-color="rgba(255,255,255,0.15)"
            />
            <div class="text-caption mt-1" style="color:rgba(255,255,255,0.5)">{{ personaStore.emotionLevel }}</div>
          </div>

          <div class="mb-4">
            <div class="d-flex justify-space-between text-caption mb-1" style="color:rgba(255,255,255,0.7)">
              <span>Self-presence · 自我觉知清晰度</span>
              <span>{{ Math.round(personaStore.selfPresenceClarity * 100) }}%</span>
            </div>
            <v-progress-linear
              :model-value="personaStore.selfPresenceClarity * 100"
              color="light-blue"
              height="6" rounded
              bg-color="rgba(255,255,255,0.12)"
            />
            <div class="d-flex justify-space-between text-caption mt-2 mb-1" style="color:rgba(255,255,255,0.7)">
              <span>Self-presence · 自我接纳</span>
              <span>{{ Math.round(personaStore.selfPresenceCompassion * 100) }}%</span>
            </div>
            <v-progress-linear
              :model-value="personaStore.selfPresenceCompassion * 100"
              color="pink-lighten-2"
              height="6" rounded
              bg-color="rgba(255,255,255,0.12)"
            />
            <div class="text-caption mt-1" style="color:rgba(255,255,255,0.56)">
              趋势：{{ formatSelfPresenceTrend(personaStore.selfPresenceTrend) }}
            </div>
          </div>

          <!-- Persona Portraits -->
          <div class="mb-4">
            <div class="text-caption font-weight-bold mb-2" style="color:rgba(255,255,255,0.82)">伙伴固定形象</div>
            <div class="d-flex align-center justify-space-between mb-2">
              <div class="portrait-meta-text">版本 v{{ onboardingProfileVersion }}</div>
              <v-chip
                size="x-small"
                :color="profileConfirmed ? 'success' : 'warning'"
                variant="tonal"
              >
                {{ profileConfirmed ? '已确认' : '待确认' }}
              </v-chip>
            </div>
            <div class="persona-portraits">
              <div class="portrait-card portrait-exiles">
                <div class="portrait-title">感知精灵</div>
                <div class="portrait-content">{{ exilesPortrait }}</div>
              </div>
              <div class="portrait-card portrait-firefighters">
                <div class="portrait-title">规则守卫</div>
                <div class="portrait-content">{{ firefightersPortrait }}</div>
              </div>
            </div>
            <div class="d-flex justify-end mt-2">
              <v-btn
                size="small"
                variant="tonal"
                color="white"
                :disabled="profileConfirmed || confirmingProfile"
                :loading="confirmingProfile"
                @click="confirmOnboardingProfile"
              >
                这是我的伙伴形象
              </v-btn>
            </div>

            <div class="archive-restore mt-3">
              <div class="archive-title">伙伴存档</div>
              <div class="d-flex align-center" style="gap:8px;">
                <v-select
                  v-model="selectedArchiveVersion"
                  :items="archiveVersionOptions"
                  item-title="title"
                  item-value="value"
                  density="compact"
                  hide-details
                  variant="outlined"
                  label="选择历史版本"
                  class="archive-select"
                />
                <v-btn
                  size="small"
                  variant="tonal"
                  color="white"
                  :loading="archiveLoading"
                  @click="reloadOnboardingArchives"
                >
                  刷新
                </v-btn>
                <v-btn
                  size="small"
                  variant="flat"
                  color="white"
                  :disabled="!selectedArchiveVersion || Number(selectedArchiveVersion) === onboardingProfileVersion"
                  :loading="archiveRestoring"
                  @click="restoreSelectedArchive"
                >
                  恢复
                </v-btn>
              </div>
            </div>
          </div>

          <!-- Session info -->
          <div class="text-caption" style="color:rgba(255,255,255,0.4)">
            <div>会话: {{ authStore.currentSessionId?.substring(0, 8) }}</div>
            <div>消息: {{ displayMessages.length }}</div>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Album side panel -->
    <Transition name="slide-right">
      <div v-if="activePanel === 'album'" class="album-panel glass-panel">
        <div class="d-flex align-center pa-3" style="border-bottom: 1px solid rgba(255,255,255,0.1)">
          <span class="text-subtitle-1 font-weight-bold" style="color:white">感知画册</span>
          <v-spacer />
          <v-btn icon variant="text" size="small" @click="activePanel = null" style="color:rgba(255,255,255,0.7)">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </div>
        <div class="overflow-y-auto" style="height: calc(100% - 52px)">
          <HealingAlbum />
        </div>
      </div>
    </Transition>

    <!-- Main Chat Area -->
    <div class="chat-main">
      <Transition name="confirm-float">
        <div v-if="showConfirmPrompt" class="confirm-floating-card glass-panel">
          <div class="confirm-title">画像解析完成</div>
          <div class="confirm-desc">请前往确认你的伙伴固定形象</div>
          <div class="d-flex justify-end mt-2" style="gap:8px;">
            <v-btn size="x-small" variant="text" color="white" @click="showConfirmPrompt = false">稍后</v-btn>
            <v-btn size="x-small" variant="tonal" color="white" @click="goConfirmProfile">前往确认</v-btn>
          </div>
        </div>
      </Transition>

      <Transition name="diary-toast">
        <div v-if="showDiaryToast" class="diary-toast glass-chip-sm">
          <v-icon size="16" color="white" class="mr-2">mdi-notebook-heart</v-icon>
          <span>{{ diaryToastText }}</span>
        </div>
      </Transition>

	      <Transition name="confirm-float">
	        <div v-if="isMemoryOrbStageVisible" class="showcase-floating-card glass-panel">
	          <div class="showcase-title">记忆球中枢</div>
	          <div class="showcase-subtitle">记忆球基于固定画像与自定义事件，触碰即可拉起内在协商。</div>
	          <div class="showcase-controls">
	            <v-btn size="x-small" variant="tonal" color="white" @click="reloadMemoryOrbs">刷新记忆球</v-btn>
	            <v-chip size="x-small" variant="tonal" color="white">
	              议题：{{ memoryOrbTopic || '点击记忆球开始' }}
	            </v-chip>
            <v-btn
              v-if="hasTriggeredOrb"
              size="x-small"
              variant="flat"
              color="white"
              @click="goToReport"
            >
              查看报告
            </v-btn>
            <v-btn
              v-else
              size="x-small"
              variant="text"
              color="white"
              disabled
	            >
	              先触碰一个记忆球
	            </v-btn>
	          </div>
	        </div>
	      </Transition>

	      <!-- Onboarding (new session, no messages) -->
	      <div v-if="authStore.needsOnboarding && displayMessages.length === 0 && !isLoading" class="onboarding-area">
	        <div class="onboarding-card glass-panel">
	          <v-icon size="42" color="rgba(255,255,255,0.72)" class="mb-3">mdi-card-text-outline</v-icon>
	          <h2 class="onboarding-title">先认识一下你</h2>
	          <p class="onboarding-subtitle">我们会根据答案为你匹配最合适的星球伙伴</p>
          <v-checkbox
            v-model="useDemoOnboardingAnswers"
            class="onboarding-demo-toggle mb-2"
            density="compact"
	            hide-details
	            color="white"
	            label="示例答案（可修改）"
	          />

          <div class="onboarding-grid mb-3">
            <v-card class="onboarding-question-card" variant="tonal">
              <v-card-text>
                <div class="onboarding-question-text mb-2">1. 描述一个让你感到不舒服的感官体验（比如噪音、强光、某种触感），你通常怎么应对？</div>
                <v-textarea class="onboarding-answer-input" v-model="onboardingAnswers.question_1" rows="2" auto-grow hide-details variant="outlined" placeholder="简要描述即可" />
              </v-card-text>
            </v-card>

            <v-card class="onboarding-question-card" variant="tonal">
              <v-card-text>
                <div class="onboarding-question-text mb-2">2. 当日常安排突然改变时，你会有什么反应？你有什么特别的兴趣或习惯？</div>
                <v-textarea class="onboarding-answer-input" v-model="onboardingAnswers.question_2" rows="2" auto-grow hide-details variant="outlined" placeholder="鼓励写原话，也可以用几个词描述自己" />
              </v-card-text>
            </v-card>
          </div>

          <div class="d-flex justify-end">
            <v-btn color="white" variant="tonal" :loading="onboardingSubmitting" :disabled="!canSubmitOnboarding" @click="submitOnboarding">
              提交并生成画像
            </v-btn>
          </div>
        </div>
      </div>

	      <!-- Messages -->
	      <div v-else ref="messageBox" class="message-area" :class="{ 'with-memory-orb-stage': isMemoryOrbStageVisible }">
	        <div v-if="isMemoryOrbStageVisible" class="memory-orb-stage">
	          <div class="memory-orb-title">记忆球中枢</div>
	          <div class="memory-orb-hint">触碰任意记忆球，它会浮出一个瞬间，也会让某个声音走到台前</div>
	          <div v-if="!hasTriggeredOrb" class="memory-orb-cta">
	            <v-icon size="16" color="white" class="mr-1">mdi-gesture-tap</v-icon>
            触碰第一颗记忆球，故事会开始长出来
          </div>
          <div v-else class="memory-orb-cta success">
            <v-icon size="16" color="white" class="mr-1">mdi-check-circle-outline</v-icon>
            已唤醒 {{ awakenedOrbCount }} 段记忆，可前往报告查看你的内心地图
          </div>
	          <div v-if="displayMemoryOrbs.length" class="memory-orb-cluster">
	            <button
	              v-for="(orb, index) in displayMemoryOrbs"
	              :key="orb.id"
	              class="memory-orb"
	              :style="memoryOrbStyle(orb, index)"
	              @click="activateMemoryOrb(orb)"
	            >
	              <span class="memory-orb-name">{{ orb.title }}</span>
	              <span v-if="orb.triggerEvent" class="memory-orb-topic">{{ orb.triggerEvent }}</span>
	            </button>
	          </div>
	          <div v-else class="memory-orb-empty">当前没有可用记忆球，可在下方自定义。</div>

          <div class="custom-orb-toggle">
            <v-btn size="x-small" variant="tonal" color="white" @click="showCustomOrbPanel = !showCustomOrbPanel">
              {{ showCustomOrbPanel ? '收起新建' : '新建记忆球' }}
            </v-btn>
          </div>

          <div v-if="showCustomOrbPanel" class="custom-orb-panel">
            <div class="custom-orb-title">录入你的关键记忆吧</div>
            <v-text-field
              v-model="customOrbTitle"
              density="compact"
              variant="outlined"
              hide-details
              label="给你的记忆起个名字吧"
              class="custom-orb-input"
            />
            <v-textarea
              v-model="customOrbTraumaText"
              density="compact"
              variant="outlined"
              hide-details
              rows="2"
              auto-grow
              label="当时发生了什么？"
              class="custom-orb-input"
            />
            <v-text-field
              v-model="customOrbTrigger"
              density="compact"
              variant="outlined"
              hide-details
              label="最近发生什么事让你想起了它？"
              class="custom-orb-input"
            />
            <div class="custom-orb-actions">
              <v-btn size="x-small" variant="tonal" color="white" :loading="customOrbSaving" @click="addCustomMemoryOrb">
                添加记忆球
              </v-btn>
            </div>
          </div>
        </div>

	        <!-- Welcome guide when no messages -->
	        <div v-if="displayMessages.length === 0 && !authStore.needsOnboarding" class="welcome-guide">
	          <div class="welcome-icon">
	            <v-icon size="48" color="rgba(255,255,255,0.5)">mdi-star-shooting</v-icon>
	          </div>
          <h3 class="welcome-title">欢迎回来</h3>
          <p class="welcome-desc">试着说出你现在的感受，或者选择一个话题开始</p>
          <div class="welcome-topics">
            <button class="topic-chip glass-chip-sm" @click="sendPresetTopic('今天周围的声音让我有点不舒服')">
              声音让我不舒服
            </button>
            <button class="topic-chip glass-chip-sm" @click="sendPresetTopic('今天的安排突然变了，我有点慌')">
              安排突然变了
            </button>
            <button class="topic-chip glass-chip-sm" @click="sendPresetTopic('我想更了解自己的感受')">
              想了解自己
            </button>
          </div>
        </div>

        <div v-for="msg in displayMessages" :key="msg.id"
             :class="['message-row', msg.type === 'user' ? 'user-msg' : 'ai-msg', `persona-${msg.persona || 'manager'}`]">
          <div :class="['message-bubble-wrap', msg.type === 'user' ? 'flex-row-reverse' : 'flex-row']">
            <v-avatar
              :color="msg.type === 'user' ? 'rgba(255,255,255,0.2)' : getPersonaColor(msg.persona)"
              size="34" class="flex-shrink-0 avatar-glass">
              <v-icon color="white" size="18">{{ msg.type === 'user' ? 'mdi-account' : getPersonaIcon(msg.persona) }}</v-icon>
            </v-avatar>
            <div :class="['mx-2', msg.type === 'user' ? 'text-right' : 'text-left']">
              <div class="msg-meta">
                {{ msg.type === 'user' ? '你' : getPersonaDisplay(msg.persona) }} · {{ formatTime(msg.timestamp) }}
              </div>
              <div :class="['msg-bubble', msg.type === 'user' ? 'user-bubble' : `ai-bubble persona-bubble-${msg.persona || 'manager'}`]">
                <div class="msg-text">{{ msg.content }}</div>
              </div>
              <div v-if="msg.emotionIntensity != null" class="msg-emotion">
                情绪能量: {{ Math.round(msg.emotionIntensity * 100) }}%
              </div>
            </div>
          </div>
        </div>

        <!-- AI thinking indicator -->
        <div v-if="isLoading" class="message-row ai-msg">
          <div class="message-bubble-wrap flex-row">
            <v-avatar :color="getPersonaColor(personaStore.currentPersona)" size="34" class="flex-shrink-0 avatar-glass">
              <v-icon color="white" size="18">{{ getPersonaIcon(personaStore.currentPersona) }}</v-icon>
            </v-avatar>
            <div class="mx-2">
              <div class="msg-bubble ai-bubble thinking-bubble">
                <div class="thinking-dots">
                  <span></span><span></span><span></span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

	      <!-- Input Area (fixed bottom) -->
	      <div class="input-area">
	        <div v-if="inputSuggestions.length" class="quick-chips">
	          <button
	            v-for="item in inputSuggestions"
	            :key="item.id"
	            class="quick-chip glass-chip-sm"
	            type="button"
	            @click="applyInputSuggestion(item.text)"
	          >
	            {{ item.label }}
	          </button>
	        </div>
	        <v-form @submit.prevent="sendMessage" class="input-form">
	          <div class="input-wrap glass-input">
	            <textarea
	              ref="inputEl"
	              v-model="newMessage"
	              placeholder="在这里输入你的感受..."
	              rows="1"
	              maxlength="2000"
	              class="chat-input"
	              @keydown.enter.exact.prevent="sendMessage"
	              @input="autoResize"
	            ></textarea>
	            <button
	              type="submit"
	              class="send-btn"
	              :disabled="!newMessage.trim() || isLoading"
	            >
	              <v-icon :color="newMessage.trim() && !isLoading ? 'white' : 'rgba(255,255,255,0.3)'" size="22">mdi-send</v-icon>
	            </button>
	          </div>
	        </v-form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useDialogueStore } from '@/stores/dialogue'
import { usePersonaStore } from '@/stores/persona'
import { useSSE } from '@/composables/useSSE'
import { dialogueApi } from '@/api/dialogue'
import { councilApi } from '@/api/council'
import { demoScripts } from '@/constants/demoScripts'
import ShaderBackground from '@/components/ShaderBackground.vue'
import PersonaTransition from '@/components/PersonaTransition.vue'
import CouncilDebateLog from '@/components/CouncilDebateLog.vue'
import HealingAlbum from '@/components/HealingAlbum.vue'
import { getPersonaDisplay, getPersonaIcon, getPersonaColor, getPersonaDescription, getEmotionColor } from '@/composables/usePersona'

const router = useRouter()
const authStore = useAuthStore()
const dialogueStore = useDialogueStore()
const personaStore = usePersonaStore()

useSSE(() => (
  authStore.isAuthenticated ? authStore.currentSessionId : ''
))

const messageBox = ref(null)
const inputEl = ref(null)
const newMessage = ref('')
const isLoading = ref(false)
const showDashboard = ref(false)
const showCouncilOverlay = ref(false)
const activePanel = ref(null) // 'album' | null
const showDiaryToast = ref(false)
const diaryToastText = ref('')
const onboardingSubmitting = ref(false)
const confirmingProfile = ref(false)
const showConfirmPrompt = ref(false)
const useDemoOnboardingAnswers = ref(false)
const archiveLoading = ref(false)
const archiveRestoring = ref(false)
const onboardingArchives = ref([])
const selectedArchiveVersion = ref(null)
const standaloneMemoryOrbs = ref([])
const serverMemoryOrbs = ref([])
const serverMemoryOrbsLoading = ref(false)
const standaloneTriggeredCount = ref(0)
const standaloneLastTopic = ref('')
const showCustomOrbPanel = ref(false)
const customOrbSaving = ref(false)
const customOrbTitle = ref('')
const customOrbTrigger = ref('')
const customOrbTraumaText = ref('')
const onboardingAnswers = ref({
  question_1: '',
  question_2: '',
})
let diaryToastTimer = null
const DEMO_ONBOARDING_ANSWERS = {
  question_1: '食堂很吵的时候我会捂住耳朵，有时候会戴上耳机听白噪音。荧光灯闪烁的时候我也很难集中注意力，会一直盯着灯看。',
  question_2: '如果突然换了教室我会很紧张，需要先去看看新教室长什么样才能安心。我特别喜欢画画和拼乐高，可以一个人玩很久。'
}
const LAST_SCRIPT_KEY_PREFIX = 'starbuddy_last_script_u'
const LAST_ONBOARDING_ANSWERS_KEY_PREFIX = 'starbuddy_last_onboarding_answers_u'

// Experience progress steps
const experienceSteps = ['倾听', '感知涌现', '伙伴对话', '星球会议', '成长']
const isMemoryOrbStageVisible = computed(() => (
  authStore.isAuthenticated && (!authStore.needsOnboarding || standaloneMemoryOrbs.value.length > 0)
))
const lastScriptId = computed(() => {
  const uid = authStore.userId
  if (!uid) return ''
  try {
    return String(localStorage.getItem(`${LAST_SCRIPT_KEY_PREFIX}${uid}`) || '')
  } catch {
    return ''
  }
})
const lastScript = computed(() => {
  if (!lastScriptId.value) return null
  return demoScripts.find((script) => script.id === lastScriptId.value) || null
})
const lastOnboardingAnswers = computed(() => {
  const uid = authStore.userId
  if (!uid) return null
  try {
    const raw = String(localStorage.getItem(`${LAST_ONBOARDING_ANSWERS_KEY_PREFIX}${uid}`) || '').trim()
    if (!raw) return null
    const parsed = JSON.parse(raw)
    const q1 = String(parsed?.question_1 || '').trim()
    const q2 = String(parsed?.question_2 || '').trim()
    if (!q1 && !q2) return null
    return { question_1: q1, question_2: q2 }
  } catch {
    return null
  }
})

const normalizePersistentOrb = (rawOrb, index = 0) => {
  const title = String(rawOrb?.title || rawOrb?.belief || rawOrb?.trigger_event || '未命名记忆').trim()
  const triggerEventRaw = String(rawOrb?.triggerEvent || rawOrb?.trigger_event || '').trim()
  const triggerEvent = triggerEventRaw === '当前情绪触发' ? '' : triggerEventRaw
  const traumaText = String(rawOrb?.traumaText || rawOrb?.trauma_text || triggerEvent).trim()
  const intensityRaw = Number(rawOrb?.intensity)
  const intensity = Number.isFinite(intensityRaw)
    ? (intensityRaw > 1 ? Math.max(0, Math.min(1, intensityRaw / 10)) : Math.max(0, Math.min(1, intensityRaw)))
    : 0.58

  return {
    id: String(rawOrb?.id || `orb_${index + 1}`),
    title,
    triggerEvent,
    traumaText,
    intensity,
    personaHint: String(rawOrb?.personaHint || rawOrb?.persona_hint || (intensity >= 0.72 ? 'firefighters' : 'exiles')),
    sourceType: String(rawOrb?.sourceType || rawOrb?.source_type || 'fixed'),
    createdAt: String(rawOrb?.createdAt || rawOrb?.created_at || new Date().toISOString()),
    orbRank: Number(rawOrb?.orbRank || rawOrb?.orb_rank || index + 1),
  }
}

const onboardingSettings = computed(() => authStore.user?.settings?.ifs_onboarding || {})
const fixedMemoryOrbs = computed(() => {
  const traumaRows = Array.isArray(onboardingSettings.value?.trauma_events_fixed)
    ? onboardingSettings.value.trauma_events_fixed
    : []
  const rows = traumaRows.length
    ? traumaRows.map((event) => ({
      id: event?.event_id,
      title: event?.title,
      trigger_event: event?.trigger_event,
      trauma_text: event?.trauma_event,
      intensity: event?.intensity,
      persona_hint: event?.persona_hint,
      source_type: event?.source_type,
      created_at: event?.created_at,
      orb_rank: event?.event_rank,
    }))
    : (Array.isArray(onboardingSettings.value?.memory_orbs_fixed)
      ? onboardingSettings.value.memory_orbs_fixed
      : [])
  return rows.map((orb, index) => normalizePersistentOrb(orb, index))
})
const customMemoryOrbs = computed(() => {
  const traumaRows = Array.isArray(onboardingSettings.value?.trauma_events_custom)
    ? onboardingSettings.value.trauma_events_custom
    : []
  const rows = traumaRows.length
    ? traumaRows.map((event) => ({
      id: event?.event_id,
      title: event?.title,
      trigger_event: event?.trigger_event,
      trauma_text: event?.trauma_event,
      intensity: event?.intensity,
      persona_hint: event?.persona_hint,
      source_type: event?.source_type || 'custom',
      created_at: event?.created_at,
      orb_rank: event?.event_rank,
    }))
    : (Array.isArray(onboardingSettings.value?.memory_orbs_custom)
      ? onboardingSettings.value.memory_orbs_custom
      : [])
  return rows.map((orb, index) => normalizePersistentOrb({ ...orb, source_type: orb?.source_type || 'custom' }, index))
})
const persistentMemoryOrbs = computed(() => {
  const merged = [...fixedMemoryOrbs.value, ...customMemoryOrbs.value]
  const idSet = new Set()
  const deduped = []
  for (const orb of merged) {
    if (idSet.has(orb.id)) continue
    idSet.add(orb.id)
    deduped.push(orb)
  }
  return deduped
})

async function loadServerMemoryOrbs() {
  const sessionId = String(authStore.currentSessionId || '').trim()
  if (!authStore.isAuthenticated || !sessionId) {
    serverMemoryOrbs.value = []
    return []
  }

  serverMemoryOrbsLoading.value = true
  try {
    const res = await dialogueApi.getMemoryOrbs(sessionId)
    const raw = Array.isArray(res.data?.orbs) ? res.data.orbs : []
    const normalized = raw
      .map((orb, index) => normalizePersistentOrb(orb, index))
      .filter((orb) => orb.title)
    serverMemoryOrbs.value = normalized
    return normalized
  } catch (error) {
    console.warn('加载记忆球失败:', error)
    serverMemoryOrbs.value = []
    return []
  } finally {
    serverMemoryOrbsLoading.value = false
  }
}

const mergedMemoryOrbs = computed(() => {
  const beliefRows = Array.isArray(personaStore.coreBeliefs) ? personaStore.coreBeliefs : []
  const sseBeliefOrbs = beliefRows.slice(0, 8).map((b, index) => normalizePersistentOrb({
    id: `live_belief_${index}`,
    title: b?.content,
    trigger_event: b?.origin_event || b?.content,
    trauma_text: b?.origin_event || b?.content,
    intensity: b?.intensity,
    persona_hint: Number(b?.valence || 0) < -0.2 ? 'firefighters' : 'exiles',
    source_type: 'live_core_belief',
  }, index))

  const merged = [...persistentMemoryOrbs.value, ...serverMemoryOrbs.value, ...sseBeliefOrbs]
  const seen = new Set()
  const out = []

  for (const orb of merged) {
    const id = String(orb?.id || '').trim()
    const title = String(orb?.title || '').trim()
    const triggerEvent = String(orb?.triggerEvent || '').trim()
    const key = title ? `t:${title}|${triggerEvent}` : id ? `id:${id}` : ''

    if (!title) continue
    if (!key) continue
    if (seen.has(key)) continue
    seen.add(key)
    out.push(orb)
  }

  out.sort((a, b) => {
    const ia = Number(a?.intensity || 0)
    const ib = Number(b?.intensity || 0)
    if (ib !== ia) return ib - ia

    const ra = Number(a?.orbRank || 0)
    const rb = Number(b?.orbRank || 0)
    if (ra && rb && ra !== rb) return ra - rb

    return String(b?.createdAt || '').localeCompare(String(a?.createdAt || ''))
  })

  return out.slice(0, 12)
})

const hasTriggeredOrb = computed(() => standaloneTriggeredCount.value > 0)
const awakenedOrbCount = computed(() => standaloneTriggeredCount.value)
const memoryOrbTopic = computed(() => standaloneLastTopic.value)
const displayMemoryOrbs = computed(() => standaloneMemoryOrbs.value)
const displayMessages = computed(() => dialogueStore.messages)

const inputSuggestions = computed(() => {
  if (!authStore.isAuthenticated || authStore.needsOnboarding) return []

  const items = []
  const seen = new Set()

  const add = (id, label, text) => {
    const value = String(text || '').trim()
    if (!value) return
    if (seen.has(value)) return
    seen.add(value)
    items.push({ id, label, text: value })
  }

  const script = lastScript.value
  if (script) {
    let count = 0
    for (const scene of script.scenes || []) {
      if (scene?.type !== 'user_message') continue
      const content = String(scene?.payload?.content || '').trim()
      if (!content) continue
      const label = content.length > 12 ? `${content.slice(0, 12)}...` : content
      add(`script_${script.id}_${count}`, label, content)
      count += 1
      if (count >= 4) break
    }
  }

  add('base_confused', '我有点乱', '我现在有点乱，不知道从哪说起')
  add('base_trigger', '最近一次触发', '我想聊聊最近一次触发')
  add('base_self_blame', '停不下自责', '我想停止自责，但停不下来')

  const answers = lastOnboardingAnswers.value
  if (answers?.question_1) add('onboarding_q1', '两句1', answers.question_1)
  if (answers?.question_2) add('onboarding_q2', '两句2', answers.question_2)

  return items
})
	
	const currentStep = computed(() => {
	  if (personaStore.coreBeliefs.length > 0) return 4
	  if (personaStore.councilConclusion) return 4
  if (personaStore.isInnerCouncilActive) return 3
  if (personaStore.currentPersona === 'exiles' || personaStore.currentPersona === 'firefighters') return 2
  if (personaStore.emotionIntensity > 0.3) return 1
  if (displayMessages.value.length > 0) return 1
  return 0
})

const canSubmitOnboarding = computed(() => {
  const values = Object.values(onboardingAnswers.value)
  return values.every(v => String(v || '').trim().length > 0) && !onboardingSubmitting.value
})

// Show council overlay automatically when council starts
watch(() => personaStore.isInnerCouncilActive, (active) => {
  if (active) {
    showCouncilOverlay.value = true
    const eduKey = getEduStorageKey('council')
    if (!localStorage.getItem(eduKey)) {
      localStorage.setItem(eduKey, '1')
      dialogueStore.addSystemMessage('星球会议开始了。不同的伙伴会说出各自的想法，最后我们一起找到一个让大家都舒服的方式。')
    }
  }
})
	watch(useDemoOnboardingAnswers, (enabled) => {
	  if (!enabled) return
	  onboardingAnswers.value = { ...DEMO_ONBOARDING_ANSWERS }
	})

watch(
  () => authStore.currentSessionId,
  (sessionId) => {
    if (!sessionId) return
    void loadServerMemoryOrbs()
  },
  { immediate: true }
)

watch(mergedMemoryOrbs, () => {
	  standaloneMemoryOrbs.value = mergedMemoryOrbs.value.map((orb, index) => normalizePersistentOrb(orb, index))
	}, { deep: true, immediate: true })

const currentPersonaDisplay = computed(() => getPersonaDisplay(personaStore.currentPersona))
const emotionBarColor = computed(() => getEmotionColor(personaStore.emotionIntensity))
const emotionBarStyle = computed(() => ({
  width: `${personaStore.emotionIntensity * 100}%`,
  background: getEmotionColor(personaStore.emotionIntensity),
}))

const onboardingProfile = computed(() => authStore.user?.settings?.ifs_onboarding || {})
const onboardingProfileVersion = computed(() => Number(onboardingProfile.value?.profile_version || 1))
const profileConfirmed = computed(() => Boolean(onboardingProfile.value?.profile_confirmed))
const archiveVersionOptions = computed(() => onboardingArchives.value.map((item) => ({
  title: `v${item.profile_version} · ${item.created_at ? String(item.created_at).slice(0, 19).replace('T', ' ') : '未知时间'}`,
  value: Number(item.profile_version),
})))
const exilesPortrait = computed(() =>
  onboardingProfile.value?.persona_portraits?.exiles ||
  '问卷完成后将生成并固定在此。'
)
const firefightersPortrait = computed(() =>
  onboardingProfile.value?.persona_portraits?.firefighters ||
  '问卷完成后将生成并固定在此。'
)

const formatTime = (ts) => new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
const formatSelfPresenceTrend = (trend) => {
  if (trend === 'up') return '上升'
  if (trend === 'down') return '下降'
  return '平稳'
}

const getEduStorageKey = (suffix) => {
  const uid = String(authStore.userId || 'anon')
  return `starbuddy_edu_${suffix}_u${uid}`
}

const maybeShowPersonaEduBubble = (persona) => {
  if (persona !== 'exiles' && persona !== 'firefighters') return
  const eduKey = getEduStorageKey('persona_switch')
  if (localStorage.getItem(eduKey)) return
  localStorage.setItem(eduKey, '1')
  const eduText = persona === 'exiles'
    ? '感知精灵出现了。它承载着你对声音、光线、触感的敏锐感受。让它把感觉说完。'
    : '规则守卫出动了。它在变化和不确定中为你守护秩序，只是方式可能有点严格。'
  dialogueStore.addSystemMessage(eduText)
}

const scrollToBottom = () => {
  nextTick(() => {
    if (messageBox.value) {
      const el = messageBox.value.$el || messageBox.value
      el.scrollTop = el.scrollHeight
    }
  })
}
watch(() => displayMessages.value.length, scrollToBottom)

const autoResize = () => {
  const el = inputEl.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 120) + 'px'
}

const focusChatInput = () => {
  const el = inputEl.value
  if (el && typeof el.focus === 'function') el.focus()
}

const applyInputSuggestion = (text) => {
  const value = String(text || '').trim()
  if (!value) return
  newMessage.value = value
  nextTick(() => {
    autoResize()
    focusChatInput()
  })
}

const memoryOrbStyle = (orb, index) => {
  const intensity = Number(orb?.intensity || 0.55)
  const size = 86 + Math.round(intensity * 58)
  const hue = 292 + ((index * 19) % 30)
  const glow = 0.2 + intensity * 0.36
  return {
    width: `${size}px`,
    height: `${size}px`,
    background: `radial-gradient(circle at 30% 30%, hsla(${hue}, 84%, 78%, 0.75), hsla(${hue + 18}, 88%, 56%, 0.22))`,
    boxShadow: `0 0 0 1px rgba(255,255,255,0.18), 0 0 26px hsla(${hue + 10}, 90%, 66%, ${glow})`,
  }
}

const ensureCouncilFromMemoryOrb = async (topic) => {
  const sessionId = String(authStore.currentSessionId || '')
  const normalizedTopic = String(topic || '').trim() || '当前情绪触发'
  if (!sessionId) return false

  try {
    const activeRes = await councilApi.getActiveCouncil(sessionId)
    if (activeRes?.data?.has_active) {
      return true
    }
  } catch (error) {
    console.warn('查询活跃议会失败，将尝试直接启动:', error)
  }

  try {
    const startRes = await councilApi.startCouncil({
      session_id: sessionId,
      topic: normalizedTopic,
      max_rounds: 2,
    })
    const started = startRes?.data
    if (started?.council_id) {
      personaStore.startInnerCouncil(started.council_id, Number(started.total_rounds || 2))
      dialogueStore.addSystemMessage(`星球会议已启动：${normalizedTopic}`)
      return true
    }
  } catch (error) {
    console.error('记忆球触发议会启动失败:', error)
  }

  return false
}

const activateMemoryOrb = async (orb) => {
  if (isLoading.value) return
  const normalized = normalizePersistentOrb(orb, standaloneTriggeredCount.value)
  standaloneMemoryOrbs.value = standaloneMemoryOrbs.value.filter(item => String(item.id) !== String(normalized.id))
  standaloneTriggeredCount.value += 1
  standaloneLastTopic.value = normalized.triggerEvent || normalized.title

  const persona = normalized.personaHint || 'exiles'
  const intensity = Number(normalized.intensity || 0.58)
  personaStore.switchPersona(persona, intensity, 'manual_memory_orb')
  maybeShowPersonaEduBubble(persona)

  dialogueStore.addSystemMessage(`记忆球「${normalized.title}」已唤醒，议会主题：${standaloneLastTopic.value}`)
  const councilStarted = await ensureCouncilFromMemoryOrb(standaloneLastTopic.value)
  if (councilStarted) {
    showCouncilOverlay.value = true
  }
  if (normalized.traumaText || standaloneLastTopic.value) {
    const orbPrompt = normalized.traumaText || standaloneLastTopic.value
    isLoading.value = true
    try {
      dialogueStore.addUserMessage(orbPrompt)
      scrollToBottom()
      const response = await dialogueApi.sendMessage({
        message: orbPrompt,
        session_id: authStore.currentSessionId,
      })
      dialogueStore.addResponseMessage(
        response.data.response,
        response.data.persona,
        response.data.emotion_intensity,
        response.data.version_info,
      )
      maybeShowPersonaEduBubble(response.data.persona)
      if (response.data.council_active || councilStarted) {
        showCouncilOverlay.value = true
      }
    } catch (error) {
      console.error('记忆球触发议会失败:', error)
      dialogueStore.addSystemMessage('记忆球已触碰，但议会未成功拉起，请稍后重试。')
    } finally {
      isLoading.value = false
      scrollToBottom()
    }
  }
}

const reloadMemoryOrbs = async () => {
  standaloneTriggeredCount.value = 0
  standaloneLastTopic.value = ''
  await loadServerMemoryOrbs()
  standaloneMemoryOrbs.value = mergedMemoryOrbs.value.map((orb, index) => normalizePersistentOrb(orb, index))
}

const addCustomMemoryOrb = async () => {
  if (customOrbSaving.value) return
  const title = String(customOrbTitle.value || '').trim()
  const trigger = String(customOrbTrigger.value || '').trim()
  const traumaText = String(customOrbTraumaText.value || '').trim()
  if (!title || !trigger) {
    dialogueStore.addSystemMessage('请填写“标题”和“触发事件”后再添加。')
    return
  }

  customOrbSaving.value = true
  try {
    const orb = {
      id: `custom_${Date.now()}`,
      title,
      trigger_event: trigger,
      trauma_text: traumaText || trigger,
      intensity: 0.6,
      persona_hint: 'exiles',
      source_type: 'custom',
      created_at: new Date().toISOString(),
    }
    const settings = authStore.user?.settings || {}
    const onboarding = settings.ifs_onboarding || {}
    const customRows = Array.isArray(onboarding.memory_orbs_custom) ? [...onboarding.memory_orbs_custom] : []
    customRows.push(orb)
    const traumaRows = Array.isArray(onboarding.trauma_events_custom) ? [...onboarding.trauma_events_custom] : []
    traumaRows.push({
      event_id: orb.id,
      title: orb.title,
      trigger_event: orb.trigger_event,
      trauma_event: orb.trauma_text,
      intensity: orb.intensity,
      persona_hint: orb.persona_hint,
      source_type: orb.source_type,
      created_at: orb.created_at,
      updated_at: new Date().toISOString(),
      event_rank: traumaRows.length + 1,
    })

    const nextSettings = {
      ...settings,
      ifs_onboarding: {
        ...onboarding,
        trauma_events_custom: traumaRows,
        trauma_events_fixed: Array.isArray(onboarding.trauma_events_fixed)
          ? onboarding.trauma_events_fixed
          : [],
        trauma_events_initialized: true,
        memory_orbs_custom: customRows,
        memory_orbs_fixed: Array.isArray(onboarding.memory_orbs_fixed) ? onboarding.memory_orbs_fixed : [],
        memory_orbs_initialized: true,
      }
    }
	    const result = await authStore.updateProfile({ settings: nextSettings })
	    if (result.success) {
	      customOrbTitle.value = ''
	      customOrbTrigger.value = ''
	      customOrbTraumaText.value = ''
	      showCustomOrbPanel.value = false
	      standaloneMemoryOrbs.value = [...standaloneMemoryOrbs.value, normalizePersistentOrb(orb, standaloneMemoryOrbs.value.length)]
	      dialogueStore.addSystemMessage('已添加自定义记忆球。')
	    } else {
	      dialogueStore.addSystemMessage(result.error || '添加自定义记忆球失败，请稍后重试。')
	    }
  } catch (error) {
    console.error('添加自定义记忆球失败:', error)
    dialogueStore.addSystemMessage('添加自定义记忆球失败，请稍后重试。')
  } finally {
    customOrbSaving.value = false
  }
}

const reloadOnboardingArchives = async () => {
  if (archiveLoading.value) return
  archiveLoading.value = true
  try {
    const result = await authStore.getOnboardingArchives()
    if (result.success) {
      onboardingArchives.value = Array.isArray(result.data?.archives) ? result.data.archives : []
      if (!selectedArchiveVersion.value && onboardingArchives.value.length > 0) {
        selectedArchiveVersion.value = Number(onboardingArchives.value[0].profile_version)
      }
    } else {
      dialogueStore.addSystemMessage(result.error || '获取人格存档失败，请稍后重试。')
    }
  } catch (error) {
    console.error('获取人格存档失败:', error)
    dialogueStore.addSystemMessage('获取人格存档失败，请稍后重试。')
  } finally {
    archiveLoading.value = false
  }
}

const restoreSelectedArchive = async () => {
  const version = Number(selectedArchiveVersion.value || 0)
  if (!version || archiveRestoring.value) return
  if (version === onboardingProfileVersion.value) return

  archiveRestoring.value = true
  try {
    const result = await authStore.restoreOnboardingArchive(version, authStore.currentSessionId)
    if (result.success) {
      dialogueStore.addSystemMessage(`已恢复到人格存档 v${version}。`)
      await reloadOnboardingArchives()
    } else {
      dialogueStore.addSystemMessage(result.error || '恢复人格存档失败，请稍后重试。')
    }
  } catch (error) {
    console.error('恢复人格存档失败:', error)
    dialogueStore.addSystemMessage('恢复人格存档失败，请稍后重试。')
  } finally {
    archiveRestoring.value = false
  }
}

const goToReport = () => {
  router.push('/report')
}

const sendMessage = async () => {
  if (!newMessage.value.trim() || isLoading.value) return
  const content = newMessage.value.trim()
  newMessage.value = ''
  if (inputEl.value) inputEl.value.style.height = 'auto'
  isLoading.value = true
  try {
    dialogueStore.addUserMessage(content)
    scrollToBottom()
    const response = await dialogueApi.sendMessage({
      message: content,
      session_id: authStore.currentSessionId,
    })
    dialogueStore.addResponseMessage(
      response.data.response, response.data.persona,
      response.data.emotion_intensity, response.data.version_info
    )
    // 首次科普气泡
    maybeShowPersonaEduBubble(response.data.persona)
  } catch (error) {
    console.error('发送失败:', error)
    dialogueStore.addSystemMessage('对面的声音沉默许久，试试退出后重新登陆？')
  } finally {
    isLoading.value = false
    scrollToBottom()
  }
}

const sendPresetTopic = (topic) => {
  applyInputSuggestion(topic)
}

const submitOnboarding = async () => {
  if (!canSubmitOnboarding.value) return
  onboardingSubmitting.value = true
  try {
    const result = await authStore.submitOnboarding(onboardingAnswers.value, authStore.currentSessionId)
    if (result.success) {
      try {
        const uid = authStore.userId
        if (uid) {
          localStorage.setItem(
            `${LAST_ONBOARDING_ANSWERS_KEY_PREFIX}${uid}`,
            JSON.stringify({
              question_1: String(onboardingAnswers.value?.question_1 || ''),
              question_2: String(onboardingAnswers.value?.question_2 || ''),
            })
          )
        }
      } catch {}
      dialogueStore.addSystemMessage('画像构建完成：已更新感知精灵 / 规则守卫提示词。')
      if (!profileConfirmed.value) {
        showConfirmPrompt.value = true
      }
      await reloadOnboardingArchives()
    } else {
      dialogueStore.addSystemMessage(result.error || '问卷提交失败，请稍后重试。')
    }
  } catch (error) {
    console.error('提交问卷失败:', error)
    dialogueStore.addSystemMessage('问卷提交失败，请稍后重试。')
  } finally {
    onboardingSubmitting.value = false
  }
}

const confirmOnboardingProfile = async () => {
  if (profileConfirmed.value || confirmingProfile.value) return
  confirmingProfile.value = true
  try {
    const settings = authStore.user?.settings || {}
    const onboarding = settings.ifs_onboarding || {}
    const nextSettings = {
      ...settings,
      ifs_onboarding_completed: true,
      ifs_onboarding: {
        ...onboarding,
        profile_confirmed: true,
      }
    }
    const result = await authStore.updateProfile({ settings: nextSettings })
    if (result.success) {
      dialogueStore.addSystemMessage('已确认伙伴固定形象。')
      showConfirmPrompt.value = false
    } else {
      dialogueStore.addSystemMessage(result.error || '确认失败，请稍后重试。')
    }
  } catch (error) {
    console.error('确认画像失败:', error)
    dialogueStore.addSystemMessage('确认失败，请稍后重试。')
  } finally {
    confirmingProfile.value = false
  }
}

const goConfirmProfile = () => {
  showDashboard.value = true
  showConfirmPrompt.value = false
}

const handleLogout = async () => {
  await authStore.logout()
  router.push('/login')
}

const handleDiaryUpdateToast = (event) => {
  const persona = event?.detail?.persona
  const personaName = getPersonaDisplay(persona || 'manager')
  diaryToastText.value = `最新日记已生成（${personaName}）`
  showDiaryToast.value = true
  if (diaryToastTimer) clearTimeout(diaryToastTimer)
  diaryToastTimer = setTimeout(() => {
    showDiaryToast.value = false
  }, 2600)
}

onMounted(async () => {
  window.addEventListener('starbuddy:diary-update', handleDiaryUpdateToast)
  if (!authStore.isAuthenticated) { router.push('/login'); return }
  const ensureSession = async () => {
    try {
      const res = await dialogueApi.createSession({ session_name: '新会话' })
      authStore.setSessionId(res.data.id)
      dialogueStore.startNewSession(res.data.id)
    } catch (e) { console.error('创建会话失败:', e) }
  }
  if (!authStore.currentSessionId) {
    await ensureSession()
  } else {
    dialogueStore.currentSessionId = authStore.currentSessionId
    try {
      const res = await dialogueApi.getHistory(authStore.currentSessionId)
      const history = Array.isArray(res.data?.history) ? res.data.history : []
      if (history.length > 0) {
        const historyAsc = [...history].reverse()
        dialogueStore.messages = historyAsc.flatMap(h => {
          const rows = []
          if (h.message) {
            rows.push({
              id: `hist_${h.id}_u`,
              content: h.message,
              type: 'user',
              persona: null,
              emotionIntensity: null,
              timestamp: h.created_at,
            })
          }
          if (h.response) {
            rows.push({
              id: `hist_${h.id}_a`,
              content: h.response,
              type: 'response',
              persona: h.persona || 'manager',
              emotionIntensity: h.emotion_intensity,
              timestamp: h.created_at,
            })
          }
          return rows
        })
        dialogueStore.sessionStatus = {
          isActive: true,
          messageCount: dialogueStore.messages.length,
          lastActivity: dialogueStore.messages.length > 0
            ? dialogueStore.messages[dialogueStore.messages.length - 1].timestamp
            : new Date().toISOString(),
        }
      } else {
        // 会话没有历史时必须清空本地消息，避免沿用上一个用户的内存态
        dialogueStore.clearMessages()
      }
    } catch (e) {
      console.warn('获取历史失败:', e.response?.status)
      if (e.response?.status === 404 || e.response?.status === 500) await ensureSession()
    }
  }
  if (!authStore.needsOnboarding) {
    await reloadMemoryOrbs()
  }
  if (!authStore.needsOnboarding) {
    await reloadOnboardingArchives()
  }
  scrollToBottom()
})

onBeforeUnmount(() => {
  window.removeEventListener('starbuddy:diary-update', handleDiaryUpdateToast)
  if (diaryToastTimer) clearTimeout(diaryToastTimer)
})
</script>

<style scoped>
/* ===== Layout ===== */
.home-root {
  position: fixed;
  inset: 0;
  overflow: hidden;
}

/* ===== Glass effects ===== */
.glass-panel {
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 20px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}

.glass-chip {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 24px;
  color: white;
  transition: all 0.3s ease;
}
.glass-chip:hover {
  background: rgba(255, 255, 255, 0.15);
  transform: translateY(-1px);
}

.glass-chip-sm {
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  color: rgba(255, 255, 255, 0.8);
  transition: all 0.3s ease;
}
.glass-chip-sm:hover {
  background: rgba(255, 255, 255, 0.12);
}

.glass-input {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 28px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.05);
  transition: all 0.3s ease;
}
.input-wrap:focus-within {
  background: rgba(255, 255, 255, 0.14);
  border-color: rgba(255, 255, 255, 0.3);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
}

.glass-menu {
  background: rgba(30, 30, 50, 0.9) !important;
  backdrop-filter: blur(24px) !important;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
  border-radius: 16px !important;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.3) !important;
}

/* ===== HUD Elements ===== */
.hud-container {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 16px;
  pointer-events: none;
}

.hud-interactive {
  pointer-events: auto;
}

.hud-persona {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 14px 6px 6px;
  cursor: pointer;
}

.hud-persona-info {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.hud-persona-name {
  font-size: 13px;
  font-weight: 600;
  color: white;
}
.hud-emotion-bar {
  width: 60px;
  height: 3px;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 2px;
  overflow: hidden;
}
.hud-emotion-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.6s ease, background 0.6s ease;
}

.hud-btn {
  width: 40px;
  height: 40px;
}

/* ===== Progress Stepper ===== */
.hud-progress-centered {
  position: absolute;
  top: 16px;
  left: 50%;
  transform: translateX(-50%);
  pointer-events: auto;
}
.progress-stepper {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 14px;
  font-size: 11px;
}
.step-item {
  display: flex;
  align-items: center;
  gap: 4px;
  color: rgba(255, 255, 255, 0.62);
  transition: color 0.3s;
}
.step-item.active {
  color: white;
  font-weight: 600;
}
.step-item.completed {
  color: rgba(255, 255, 255, 0.65);
}
.step-item:not(:last-child)::after {
  content: '→';
  margin-left: 4px;
  color: rgba(255, 255, 255, 0.48);
}
.step-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 1.5px solid currentColor;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.step-item.active .step-dot {
  background: rgba(255, 255, 255, 0.25);
  box-shadow: 0 0 8px rgba(255, 255, 255, 0.3);
}
.step-item.completed .step-dot {
  background: rgba(255, 255, 255, 0.4);
}
.step-label {
  display: none;
}
@media (min-width: 768px) {
  .step-label { display: inline; }
  /* Key alignment adjustment for desktop */
  .hud-container {
    padding: 24px 18%;
  }
  .hud-progress-centered {
    top: 24px;
  }
}

/* ===== Dashboard Panel ===== */
.dashboard-panel {
  position: fixed;
  top: 80px;
  left: 16px;
  width: 280px;
  max-height: calc(100vh - 100px);
  overflow-y: auto;
  z-index: 90;
}

/* ===== Album Panel ===== */
.album-panel {
  position: fixed;
  top: 16px;
  right: 60px;
  width: 360px;
  height: calc(100vh - 32px);
  z-index: 90;
  overflow: hidden;
}

/* ===== Council Overlay ===== */
.council-overlay {
  position: fixed;
  inset: 0;
  z-index: 200;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(4px);
}
.council-overlay-inner {
  width: 90%;
  max-width: 700px;
  max-height: 80vh;
  overflow-y: auto;
  padding: 0;
}
.council-overlay-header {
  display: flex;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

/* ===== Chat Main ===== */
.chat-main {
  position: fixed;
  inset: 0;
  display: flex;
  flex-direction: column;
  z-index: 10;
  padding-top: calc(84px + env(safe-area-inset-top));
}

.diary-toast {
  position: absolute;
  top: 10px;
  right: 18%;
  z-index: 30;
  display: inline-flex;
  align-items: center;
  padding: 8px 12px;
  color: white;
  font-size: 12px;
}

.showcase-floating-card {
  position: absolute;
  top: 10px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 32;
  width: min(760px, calc(100vw - 32px));
  padding: 10px 12px;
}

.showcase-title {
  color: rgba(255, 255, 255, 0.94);
  font-size: 13px;
  font-weight: 700;
}

.showcase-subtitle {
  margin-top: 4px;
  color: rgba(255, 255, 255, 0.7);
  font-size: 11px;
}

.showcase-controls {
  margin-top: 8px;
  display: flex;
  gap: 8px;
  align-items: center;
}

.memory-orb-stage {
  position: fixed;
  left: 50%;
  bottom: calc(148px + env(safe-area-inset-bottom));
  transform: translateX(-50%);
  z-index: 34;
  width: min(860px, calc(100vw - 24px));
  max-height: min(34vh, 340px);
  overflow-y: auto;
  margin: 0;
  padding: 14px;
  border-radius: 18px;
}

.memory-orb-title {
  color: rgba(255, 255, 255, 0.94);
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.4px;
}

.memory-orb-hint {
  margin-top: 4px;
  color: rgba(255, 255, 255, 0.66);
  font-size: 12px;
}

.memory-orb-cta {
  margin-top: 10px;
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.9);
  background: rgba(255, 255, 255, 0.12);
  border: 1px solid rgba(255, 255, 255, 0.24);
}

.memory-orb-cta.success {
  background: rgba(74, 222, 128, 0.18);
  border-color: rgba(74, 222, 128, 0.38);
}

.memory-orb-cluster {
  margin-top: 14px;
  display: flex;
  flex-wrap: nowrap;
  justify-content: center;
  align-items: flex-end;
  gap: 0;
  overflow-x: auto;
  padding: 4px 6px;
}

.memory-orb {
  border: none;
  border-radius: 999px;
  color: white;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 10px;
  transition: transform 0.24s ease, box-shadow 0.24s ease;
  margin-left: -10px;
  flex-shrink: 0;
}

.memory-orb:first-child {
  margin-left: 0;
}

.memory-orb:hover {
  transform: translateY(-2px) scale(1.02);
}

.memory-orb-name {
  font-size: 14px;
  font-weight: 700;
  text-shadow: 0 1px 6px rgba(0, 0, 0, 0.35);
}

.memory-orb-topic {
  margin-top: 4px;
  font-size: 11px;
  opacity: 0.9;
  max-width: 92%;
  line-height: 1.3;
  text-shadow: 0 1px 6px rgba(0, 0, 0, 0.35);
}

.memory-orb-empty {
  margin-top: 14px;
  color: rgba(255, 255, 255, 0.6);
  font-size: 12px;
  text-align: center;
}

.custom-orb-toggle {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}

.custom-orb-panel {
  margin-top: 14px;
  padding: 10px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.14);
}

.custom-orb-title {
  color: rgba(255, 255, 255, 0.88);
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 8px;
}

.custom-orb-input {
  margin-bottom: 8px;
}

.custom-orb-input :deep(.v-field) {
  background: rgba(255, 255, 255, 0.08) !important;
}

.custom-orb-input :deep(.v-label),
.custom-orb-input :deep(input),
.custom-orb-input :deep(textarea) {
  color: rgba(255, 255, 255, 0.9) !important;
}

.custom-orb-actions {
  display: flex;
  justify-content: flex-end;
}

.archive-restore {
  margin-top: 10px;
}

.archive-title {
  color: rgba(255, 255, 255, 0.82);
  font-size: 12px;
  margin-bottom: 6px;
}

.archive-select {
  flex: 1;
}

.archive-select :deep(.v-field) {
  background: rgba(255, 255, 255, 0.08) !important;
}

.archive-select :deep(.v-label),
.archive-select :deep(input) {
  color: rgba(255, 255, 255, 0.9) !important;
}
@media (max-width: 767px) {
  .diary-toast {
    right: 16px;
  }

  .showcase-floating-card {
    top: 8px;
    width: calc(100vw - 20px);
    left: 10px;
    transform: none;
  }

  .showcase-controls {
    flex-wrap: wrap;
  }

  .showcase-controls {
    flex-wrap: wrap;
  }

  .memory-orb-stage {
    width: calc(100vw - 16px);
    bottom: calc(142px + env(safe-area-inset-bottom));
    padding: 12px;
    max-height: min(40vh, 360px);
  }

  .memory-orb-cluster {
    justify-content: flex-start;
  }

  .custom-orb-panel {
    padding: 8px;
  }

  .archive-restore .d-flex {
    flex-wrap: wrap;
  }
}

/* ===== Onboarding ===== */
.onboarding-area {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px 24px calc(132px + env(safe-area-inset-bottom));
}
.onboarding-card {
  text-align: center;
  padding: 48px 36px;
  max-width: 980px;
  width: min(980px, 100%);
}
.onboarding-title {
  font-size: 24px;
  font-weight: 700;
  color: white;
  margin-bottom: 12px;
  letter-spacing: 1px;
}
.onboarding-subtitle {
  font-size: 15px;
  color: rgba(255, 255, 255, 0.82);
  margin-bottom: 28px;
  line-height: 1.5;
}
.onboarding-demo-toggle {
  display: inline-flex;
}
.onboarding-demo-toggle :deep(.v-label) {
  color: rgba(255, 255, 255, 0.9) !important;
}
.onboarding-demo-toggle :deep(.v-selection-control__input > .v-icon) {
  color: rgba(255, 255, 255, 0.92) !important;
}
.onboarding-question-card {
  background: rgba(18, 22, 35, 0.6) !important;
  border: 1px solid rgba(255, 255, 255, 0.24) !important;
}
.onboarding-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
}
.onboarding-question-text {
  color: rgba(255, 255, 255, 0.92);
  font-size: 14px;
  font-weight: 500;
}
.onboarding-answer-input :deep(.v-field) {
  background: rgba(255, 255, 255, 0.12) !important;
}
.onboarding-answer-input :deep(textarea) {
  color: rgba(255, 255, 255, 0.95) !important;
}
.onboarding-answer-input :deep(textarea::placeholder) {
  color: rgba(255, 255, 255, 0.78) !important;
}
.onboarding-answer-input :deep(.v-field__outline) {
  color: rgba(255, 255, 255, 0.36) !important;
}
.onboarding-topics {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.topic-btn {
  padding: 12px 20px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
  text-align: left;
}
.topic-btn:hover {
  background: rgba(255, 255, 255, 0.18);
  transform: translateX(4px);
}

.confirm-floating-card {
  position: absolute;
  top: 12px;
  right: 16px;
  z-index: 35;
  width: 280px;
  padding: 12px;
}

.confirm-title {
  color: rgba(255, 255, 255, 0.95);
  font-size: 13px;
  font-weight: 700;
}

.confirm-desc {
  color: rgba(255, 255, 255, 0.78);
  font-size: 12px;
  margin-top: 4px;
}

.persona-portraits {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.portrait-card {
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  background: rgba(255, 255, 255, 0.08);
  padding: 10px 12px;
}

.portrait-title {
  font-size: 12px;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.92);
  margin-bottom: 6px;
}

.portrait-meta-text {
  color: rgba(255, 255, 255, 0.7);
  font-size: 11px;
}

.portrait-content {
  color: rgba(255, 255, 255, 0.84);
  font-size: 12px;
  line-height: 1.5;
}

.portrait-exiles {
  border-left: 3px solid rgba(255, 140, 50, 0.8);
}

.portrait-firefighters {
  border-left: 3px solid rgba(220, 70, 70, 0.8);
}

/* ===== Messages ===== */
.message-area {
  flex: 1;
  overflow-y: auto;
  padding: 16px 24px 8px;
  scroll-behavior: smooth;
}
.message-area.with-memory-orb-stage {
  padding-bottom: calc(420px + env(safe-area-inset-bottom));
}
@media (min-width: 768px) {
  .message-area {
    padding: 16px 18% 8px;
  }

  .message-area.with-memory-orb-stage {
    padding-bottom: 400px;
  }
}

.message-row {
  display: flex;
  margin-bottom: 20px;
  animation: msg-in 0.35s ease-out;
}
.message-row.user-msg { justify-content: flex-end; }
.message-row.ai-msg { justify-content: flex-start; }

@keyframes msg-in {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

.message-bubble-wrap {
  display: flex;
  gap: 0;
  max-width: 75%;
}

.avatar-glass {
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.msg-meta {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.5);
  margin-bottom: 4px;
}

.msg-bubble {
  padding: 10px 16px;
  border-radius: 16px;
  word-break: break-word;
  line-height: 1.6;
  font-size: 14px;
}

.user-bubble {
  background: rgba(255, 255, 255, 0.18);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: white;
  border-top-right-radius: 4px;
}

.ai-bubble {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.12);
  color: rgba(255, 255, 255, 0.95);
  border-top-left-radius: 4px;
}

/* Persona-specific bubble styles */
.persona-bubble-manager {
  border-left: 3px solid rgba(90, 150, 255, 0.7);
}
.persona-bubble-exiles {
  border-left: 3px solid rgba(255, 140, 50, 0.7);
}
.persona-bubble-firefighters {
  border-left: 3px solid rgba(200, 60, 60, 0.7);
}
.persona-bubble-counselor {
  background: rgba(120, 80, 200, 0.15);
  border: 1px solid rgba(150, 100, 255, 0.25);
  border-left: 3px solid rgba(150, 100, 255, 0.7);
}

.msg-text {
  white-space: pre-wrap;
}

.msg-emotion {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.4);
  margin-top: 4px;
}

/* Thinking dots */
.thinking-bubble {
  padding: 14px 20px;
}
.thinking-dots {
  display: flex;
  gap: 6px;
}
.thinking-dots span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.5);
  animation: thinking-bounce 1.2s infinite;
}
.thinking-dots span:nth-child(2) { animation-delay: 0.2s; }
.thinking-dots span:nth-child(3) { animation-delay: 0.4s; }

@keyframes thinking-bounce {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
  30% { transform: translateY(-8px); opacity: 1; }
}

/* ===== Input Area ===== */
.input-area {
  padding: 12px 24px calc(20px + env(safe-area-inset-bottom));
}

.quick-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}

.quick-chip {
  border: none;
  cursor: pointer;
  padding: 6px 10px;
  font-size: 11px;
}

.quick-chip-hint {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.56);
}
@media (min-width: 768px) {
  .chat-main {
    padding-top: calc(100px + env(safe-area-inset-top));
  }

  .input-area {
    padding: 12px 18% 24px;
  }

  .onboarding-area {
    padding: 32px 18% calc(140px + env(safe-area-inset-bottom));
  }
}

.input-form {
  width: 100%;
}
.input-wrap {
  display: flex;
  align-items: flex-end;
  padding: 8px 8px 8px 18px;
  gap: 8px;
}
.chat-input {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  color: white;
  font-size: 14px;
  line-height: 1.5;
  resize: none;
  max-height: 120px;
  min-height: 24px;
  font-family: inherit;
}
.chat-input::placeholder {
  color: rgba(255, 255, 255, 0.65);
}
.send-btn {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: none;
  background: rgba(255, 255, 255, 0.12);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  flex-shrink: 0;
}
.send-btn:not(:disabled):hover {
  background: rgba(255, 255, 255, 0.22);
}
.send-btn:disabled {
  cursor: default;
  opacity: 0.5;
}

/* ===== Transitions ===== */
.slide-left-enter-active,
.slide-left-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.slide-left-enter-from,
.slide-left-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}

.slide-right-enter-active,
.slide-right-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.slide-right-enter-from,
.slide-right-leave-to {
  opacity: 0;
  transform: translateX(20px);
}

.council-overlay-enter-active,
.council-overlay-leave-active {
  transition: all 0.4s ease;
}
.council-overlay-enter-from,
.council-overlay-leave-to {
  opacity: 0;
}
.council-overlay-enter-from .council-overlay-inner,
.council-overlay-leave-to .council-overlay-inner {
  transform: scale(0.9);
}

.diary-toast-enter-active,
.diary-toast-leave-active {
  transition: all 0.24s ease;
}
.diary-toast-enter-from,
.diary-toast-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

.confirm-float-enter-active,
.confirm-float-leave-active {
  transition: all 0.22s ease;
}

.confirm-float-enter-from,
.confirm-float-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

/* ===== Scrollbar ===== */
.message-area::-webkit-scrollbar {
  width: 4px;
}
.message-area::-webkit-scrollbar-track {
  background: transparent;
}
.message-area::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.15);
  border-radius: 2px;
}

/* ===== Welcome Guide ===== */
.welcome-guide {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
  padding: 40px 24px;
  gap: 12px;
}
.welcome-icon {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.06);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 8px;
}
.welcome-title {
  font-size: 22px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.85);
}
.welcome-desc {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.5);
  max-width: 300px;
}
.welcome-topics {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  margin-top: 16px;
}
.topic-chip {
  padding: 10px 16px;
  font-size: 13px;
  cursor: pointer;
  border: none;
  color: rgba(255, 255, 255, 0.8);
  transition: all 0.2s;
}
.topic-chip:hover {
  background: rgba(255, 255, 255, 0.15);
  transform: translateY(-2px);
}
</style>
