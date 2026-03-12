<template>
  <div class="login-root">
    <!-- Shader Background -->
    <ShaderBackground role="manager" :intensity="0.15" />

    <div class="login-content">
      <!-- Logo and title -->
      <div class="login-header">
        <div class="logo-wrap">
          <v-icon size="40" color="white">mdi-star-shooting</v-icon>
        </div>
        <h1 class="login-title">星伴</h1>
        <p class="login-tagline">你的星球伙伴，陪你理解自己</p>
      </div>

      <!-- IFS 简介 -->
      <p class="ifs-intro">你的内心住着不同的伙伴——有感受细腻的精灵，也有守护秩序的卫士。<br>在这里，它们可以一起帮助你。</p>

      <!-- Concept cards -->
      <div class="concept-cards">
        <div class="concept-card" v-for="card in conceptCards" :key="card.name">
          <v-icon :color="card.color" size="28" class="mb-2">{{ card.icon }}</v-icon>
          <div class="concept-name" :style="{ color: card.color }">{{ card.name }}</div>
          <div class="concept-desc">{{ card.desc }}</div>
        </div>
      </div>

      <!-- 了解更多 -->
      <div class="learn-more-toggle" @click="showLearnMore = !showLearnMore">
        <v-icon size="16" class="mr-1" style="color:rgba(255,255,255,0.6)">
          {{ showLearnMore ? 'mdi-chevron-up' : 'mdi-chevron-down' }}
        </v-icon>
        <span>{{ showLearnMore ? '收起' : '了解更多：星伴是什么？' }}</span>
      </div>

      <Transition name="fade">
        <div v-if="showLearnMore" class="learn-more-cards">
          <div class="story-card" v-for="(step, i) in storySteps" :key="i">
            <div class="story-step-num">{{ i + 1 }}</div>
            <div class="story-step-title">{{ step.title }}</div>
            <div class="story-step-desc">{{ step.desc }}</div>
          </div>
        </div>
      </Transition>

      <!-- Login form -->
      <div class="login-form-wrap glass-panel">
        <v-form @submit.prevent="handleQuickLogin" :disabled="isLoading">
          <v-text-field
            v-model="username"
            label="用户名"
            prepend-inner-icon="mdi-account"
            variant="outlined"
            :error-messages="errors.username"
            hint="输入用户名即可自动登录或注册"
            persistent-hint
            class="mb-4"
            required
            density="comfortable"
            color="white"
            base-color="rgba(255,255,255,0.5)"
          ></v-text-field>

          <v-btn
            type="submit"
            color="white"
            size="large"
            block
            variant="tonal"
            :loading="isLoading"
            class="text-none login-btn"
          >
            <v-icon start>mdi-arrow-right-circle</v-icon>
            进入星伴世界
          </v-btn>
        </v-form>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-root {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow-x: hidden;
  overflow-y: auto;
}

.login-content {
  position: relative;
  z-index: 10;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 32px;
  padding: 24px;
  padding-bottom: 56px;
  max-width: 420px;
  width: 100%;
}

.login-header {
  text-align: center;
}

.logo-wrap {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
}

.login-title {
  font-size: 36px;
  font-weight: 700;
  color: white;
  letter-spacing: 3px;
  margin-bottom: 8px;
  text-shadow: 0 2px 12px rgba(0, 0, 0, 0.3);
}

.login-tagline {
  font-size: 15px;
  color: rgba(255, 255, 255, 0.7);
  letter-spacing: 2px;
}

/* Concept cards */
.concept-cards {
  display: flex;
  gap: 12px;
  width: 100%;
}

.concept-card {
  flex: 1;
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 14px;
  padding: 16px 12px;
  text-align: center;
  transition: transform 0.3s ease, background 0.3s ease;
}

.concept-card:hover {
  transform: translateY(-4px);
  background: rgba(255, 255, 255, 0.14);
}

.concept-name {
  font-size: 13px;
  font-weight: 700;
  margin-bottom: 4px;
}

.concept-desc {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.6);
  line-height: 1.4;
}

/* Login form */
.glass-panel {
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 16px;
}

.login-form-wrap {
  width: 100%;
  padding: 28px 24px;
}

.login-btn {
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 2px;
}

/* Fix Vuetify text field colors for dark bg */
:deep(.v-field__outline) {
  --v-field-border-opacity: 0.3;
}
:deep(.v-field--focused .v-field__outline) {
  --v-field-border-opacity: 0.6;
}
:deep(.v-input .v-messages) {
  color: rgba(255, 255, 255, 0.5) !important;
}
:deep(.v-text-field input) {
  color: white !important;
}
:deep(.v-field__input::placeholder) {
  color: rgba(255, 255, 255, 0.4) !important;
}
:deep(.v-label) {
  color: rgba(255, 255, 255, 0.6) !important;
}

/* IFS intro */
.ifs-intro {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.65);
  text-align: center;
  line-height: 1.7;
  max-width: 360px;
}

/* Learn more toggle */
.learn-more-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.5);
  transition: color 0.2s;
}
.learn-more-toggle:hover {
  color: rgba(255, 255, 255, 0.8);
}

/* Story cards */
.learn-more-cards {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
}
.story-card {
  background: rgba(255, 255, 255, 0.06);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 14px 16px;
  display: flex;
  align-items: flex-start;
  gap: 12px;
}
.story-step-num {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.12);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.8);
  flex-shrink: 0;
}
.story-step-title {
  font-size: 13px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.85);
  margin-bottom: 4px;
}
.story-step-desc {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.55);
  line-height: 1.5;
}

/* Fade transition */
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}
</style>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import ShaderBackground from '@/components/ShaderBackground.vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const username = ref('')

const errors = ref({
  username: ''
})

const isLoading = computed(() => authStore.isLoading)

const showLearnMore = ref(false)

const focusUsernameInput = () => {
  void nextTick(() => {
    const input = document.querySelector('.login-form-wrap input')
    if (input && typeof input.focus === 'function') input.focus()
  })
}

const handleFocusEvent = () => focusUsernameInput()

onMounted(() => {
  window.addEventListener('starbuddy:login-focus', handleFocusEvent)
  // Autofocus to make the first action obvious.
  focusUsernameInput()
})

onBeforeUnmount(() => {
  window.removeEventListener('starbuddy:login-focus', handleFocusEvent)
})

const conceptCards = [
  { name: '感知精灵', desc: '帮你理解那些让你不舒服的感官体验', icon: 'mdi-creation', color: '#F4B183' },
  { name: '规则守卫', desc: '在变化中守护你需要的秩序和安全感', icon: 'mdi-shield-star', color: '#A9D18E' },
  { name: '星球会议', desc: '让不同的伙伴坐下来一起想办法', icon: 'mdi-account-group', color: '#B4A7D6' },
]

const storySteps = [
  { title: '每个人的内心都有不同的伙伴', desc: '星伴认为，我们的内心有不同的"伙伴"，它们各自关注不同的事情，帮助我们应对世界。' },
  { title: '有的伙伴感受细腻，有的守护秩序', desc: '"感知精灵"帮你理解感官体验；"规则守卫"在变化中为你找到安全感。' },
  { title: '当它们一起合作，你就能更了解自己', desc: '通过星球会议，这些伙伴可以互相理解。这就是认识自己的开始。' },
]

const validateForm = () => {
  let valid = true
  errors.value = { username: '' }

  if (!username.value.trim()) {
    errors.value.username = '请输入用户名'
    valid = false
  } else if (username.value.trim().length < 3) {
    errors.value.username = '用户名至少需要3个字符'
    valid = false
  }

  return valid
}

const handleQuickLogin = async () => {
  if (!validateForm()) return

  const result = await authStore.quickLogin(username.value)

  if (result.success) {
    const nextPathRaw = route.query?.next
    const nextPath = typeof nextPathRaw === 'string' ? nextPathRaw : ''
    const safeNext =
      nextPath &&
      nextPath.startsWith('/') &&
      !nextPath.startsWith('//') &&
      nextPath !== '/login'

    if (safeNext) {
      router.replace(nextPath)
      return
    }
    router.replace('/')
  } else {
    if (result.error) {
       errors.value.username = result.error
    }
  }
}
</script>
