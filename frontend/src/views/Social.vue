<template>
  <div class="social-root">
    <ShaderBackground role="manager" :intensity="0.15" />

    <div class="social-scroll">
      <!-- Header -->
      <div class="social-header">
        <v-btn icon variant="text" size="small" @click="$router.back()" class="back-btn">
          <v-icon>mdi-arrow-left</v-icon>
        </v-btn>
        <h1 class="social-title">星际连线</h1>
        <p class="social-subtitle">发现与你相似的星球伙伴</p>
      </div>

      <!-- Tabs -->
      <div class="social-tabs">
        <v-btn-toggle v-model="activeTab" mandatory density="compact" variant="outlined" color="white">
          <v-btn value="resonance" size="small" class="text-none">连线匹配</v-btn>
          <v-btn value="bottle" size="small" class="text-none">漂流瓶</v-btn>
        </v-btn-toggle>
      </div>

      <!-- Resonance Tab -->
      <div v-if="activeTab === 'resonance'">
        <div v-if="similarLoading" class="loading-state">
          <v-progress-circular indeterminate color="white" size="28" />
          <span class="ml-3">正在寻找共振…</span>
        </div>
        <div v-else-if="!similarUsers.length" class="empty-state">
          <v-icon size="48" style="color:rgba(255,255,255,0.25)">mdi-account-search</v-icon>
          <p>暂时没有找到连线的伙伴</p>
          <p class="sub-text">继续探索，让更多人发现你</p>
        </div>
        <div v-else class="similar-list">
          <div v-for="(u, i) in similarUsers" :key="i" class="similar-card glass-card">
            <div class="similar-header">
              <v-avatar color="rgba(255,255,255,0.12)" size="36">
                <v-icon color="white" size="20">mdi-account-heart</v-icon>
              </v-avatar>
              <div class="similar-info">
                <div class="similar-name">
                  <span class="name-text">{{ u.name || `星际伙伴 #${u.anonymous_id}` }}</span>
                  <span v-if="u.theme" class="theme-tag">{{ u.theme }}</span>
                  <span v-if="u.profile_kind === 'guide'" class="kind-tag">引导者</span>
                </div>
                <div class="similar-score">连线度 {{ (u.similarity * 100).toFixed(0) }}%</div>
              </div>
            </div>
            <div class="similar-beliefs" v-if="u.shared_beliefs && u.shared_beliefs.length">
              <span v-for="b in u.shared_beliefs" :key="b" class="belief-tag">{{ b }}</span>
            </div>
            <div class="similar-portraits">
              <p v-if="u.exiles_summary" class="portrait-line"><span style="color:#F4B183">感知精灵：</span>{{ u.exiles_summary }}</p>
              <p v-if="u.firefighters_summary" class="portrait-line"><span style="color:#A9D18E">规则守卫：</span>{{ u.firefighters_summary }}</p>
            </div>
            <v-btn
              v-if="canOpenDialogue(u)"
              variant="tonal" color="white" size="small" class="text-none mt-3"
              @click="openChat(u)"
            >
              <v-icon start size="16">mdi-chat</v-icon>
              开启连线对话
            </v-btn>
            <v-btn
              v-else
              variant="tonal" color="white" size="small" class="text-none mt-3"
              @click="sendEncouragement(u.anonymous_id)"
              :disabled="u.encouraged"
            >
              <v-icon start size="16">mdi-heart</v-icon>
              {{ u.encouraged ? '已发送鼓励' : '发送匿名鼓励' }}
            </v-btn>
          </div>
        </div>
      </div>

      <!-- Bottle Tab -->
      <div v-if="activeTab === 'bottle'">
        <!-- Send bottle -->
        <div class="bottle-section">
          <h3 class="section-label">投放漂流瓶</h3>
          <p class="section-desc">把你的一段内心写进瓶子，让它漂到另一个人手里</p>
          <div class="bottle-form glass-card">
            <v-select
              v-model="bottlePersona"
              :items="bottlePersonaOptions"
              label="选择伙伴"
              variant="outlined"
              density="compact"
              color="white"
              base-color="rgba(255,255,255,0.4)"
              class="mb-3"
            />
            <v-textarea
              v-model="bottleMessage"
              label="附言（可选）"
              variant="outlined"
              density="compact"
              rows="2"
              color="white"
              base-color="rgba(255,255,255,0.4)"
              class="mb-3"
            />
            <v-btn
              variant="tonal" color="white" size="small" class="text-none"
              :loading="bottleSending"
              @click="sendBottle"
              :disabled="!bottlePersona"
            >
              <v-icon start size="16">mdi-bottle-wine</v-icon>
              投入大海
            </v-btn>
          </div>
        </div>

        <!-- Pick up bottle -->
        <div class="bottle-section">
          <h3 class="section-label">捡起漂流瓶</h3>
          <div v-if="pickedBottle" class="picked-bottle glass-card">
            <div class="bottle-persona-label" :style="{color: personaLabelColor(pickedBottle.persona_type)}">
              {{ personaLabel(pickedBottle.persona_type) }}
            </div>
            <p class="bottle-portrait">{{ pickedBottle.persona_portrait }}</p>
            <p v-if="pickedBottle.diary_text" class="bottle-diary">{{ pickedBottle.diary_text }}</p>
            <p v-if="pickedBottle.message" class="bottle-msg">「{{ pickedBottle.message }}」</p>
          </div>
          <div v-else class="empty-state" style="padding:24px 0">
            <v-btn
              variant="tonal" color="white" size="small" class="text-none"
              :loading="bottlePicking"
              @click="pickBottle"
            >
              <v-icon start size="16">mdi-waves</v-icon>
              从海里捡一个
            </v-btn>
          </div>
        </div>

        <!-- My bottles -->
        <div class="bottle-section" v-if="myBottles.length">
          <h3 class="section-label">我的漂流瓶</h3>
          <div v-for="b in myBottles" :key="b.id" class="my-bottle glass-card">
            <div class="bottle-status">{{ b.status === 'picked' ? '已被捡起' : '漂流中…' }}</div>
            <div class="bottle-persona-label" :style="{color: personaLabelColor(b.persona_type)}">
              {{ personaLabel(b.persona_type) }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Agent Chat Overlay -->
    <Teleport to="body">
      <div v-if="chatOpen" class="chat-overlay" @click.self="closeChat">
        <div class="chat-panel glass-card">
          <!-- Chat Header -->
          <div class="chat-header">
            <div class="chat-header-info">
              <v-avatar color="rgba(255,255,255,0.12)" size="32">
                <v-icon color="white" size="18">mdi-account-heart</v-icon>
              </v-avatar>
              <div class="chat-header-text">
                <div class="chat-agent-name">
                  <span class="name-text">{{ chatAgent?.name || `星际伙伴 #${chatAgent?.anonymous_id}` }}</span>
                  <span v-if="chatAgent?.theme" class="theme-tag">{{ chatAgent.theme }}</span>
                </div>
                <div class="chat-agent-theme" v-if="chatAgent?.shared_beliefs?.length">
                  {{ chatAgent.shared_beliefs.join(' · ') }}
                </div>
              </div>
            </div>
            <v-btn icon variant="text" size="x-small" @click="closeChat" class="chat-close-btn">
              <v-icon size="20">mdi-close</v-icon>
            </v-btn>
          </div>

          <!-- Agent Portraits Summary -->
          <div class="chat-portraits" v-if="chatAgent?.exiles_summary || chatAgent?.firefighters_summary">
            <p v-if="chatAgent.exiles_summary" class="portrait-line"><span style="color:#F4B183">感知精灵：</span>{{ chatAgent.exiles_summary }}</p>
            <p v-if="chatAgent.firefighters_summary" class="portrait-line"><span style="color:#A9D18E">规则守卫：</span>{{ chatAgent.firefighters_summary }}</p>
          </div>

          <!-- Chat Messages -->
          <div class="chat-messages" ref="chatMessagesEl">
            <div v-if="!chatMessages.length" class="chat-empty">
              <p>开始和这位星际伙伴对话吧</p>
            </div>
            <div
              v-for="(msg, idx) in chatMessages"
              :key="idx"
              class="chat-msg"
              :class="msg.role === 'user' ? 'chat-msg-user' : 'chat-msg-agent'"
            >
              <div class="chat-bubble" :class="msg.role === 'user' ? 'bubble-user' : 'bubble-agent'">
                {{ msg.content }}
              </div>
            </div>
            <div v-if="chatSending" class="chat-msg chat-msg-agent">
              <div class="chat-bubble bubble-agent chat-typing">
                <v-progress-circular indeterminate color="white" size="16" width="2" />
                <span class="ml-2">思考中…</span>
              </div>
            </div>
          </div>

          <!-- Chat Input -->
          <div class="chat-input-area">
            <div class="chat-input-wrap glass-input">
              <textarea
                ref="chatInputEl"
                v-model="chatInput"
                placeholder="输入消息…"
                rows="1"
                @keydown.enter.exact.prevent="sendChatMessage"
                @input="autoResizeChatInput"
              ></textarea>
              <v-btn
                icon
                variant="text"
                size="small"
                :disabled="!chatInput.trim() || chatSending"
                @click="sendChatMessage"
                class="chat-send-btn"
              >
                <v-icon size="20">mdi-send</v-icon>
              </v-btn>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import ShaderBackground from '@/components/ShaderBackground.vue'
import { useAuthStore } from '@/stores/auth'
import { useShowcaseStore } from '@/stores/showcase'

const router = useRouter()
const route = useRoute()

const baseURL = import.meta.env.VITE_API_URL || ''
const getToken = () => localStorage.getItem('access_token')
const authHeaders = () => ({ 'X-Auth-Token': getToken() })
const authStore = useAuthStore()
const showcaseStore = useShowcaseStore()
const isShowcaseActive = computed(() => showcaseStore.active)

const activeTab = ref('resonance')
const similarLoading = ref(false)
const similarUsers = ref([])
const bottlePersona = ref(null)
const bottleMessage = ref('')
const bottleSending = ref(false)
const bottlePicking = ref(false)
const pickedBottle = ref(null)
const myBottles = ref([])
const bottlePersonaOptions = [
  { title: '感知精灵', value: 'exiles' },
  { title: '规则守卫', value: 'firefighters' },
  { title: '安全岛', value: 'manager' },
  { title: '温柔旁观者', value: 'witness' },
  { title: '匿名留声', value: 'echo' },
  { title: '海边灯塔', value: 'lighthouse' },
  { title: '夜航者', value: 'night_sailor' },
  { title: '旧信纸', value: 'old_letter' },
  { title: '静默花园', value: 'quiet_garden' },
  { title: '掌心余温', value: 'warm_palm' },
]

const personaLabelMap = {
  exiles: '感知精灵',
  firefighters: '规则守卫',
  manager: '安全岛',
  witness: '温柔旁观者',
  echo: '匿名留声',
  lighthouse: '海边灯塔',
  night_sailor: '夜航者',
  old_letter: '旧信纸',
  quiet_garden: '静默花园',
  warm_palm: '掌心余温',
}

const personaColorMap = {
  exiles: '#F4B183',
  firefighters: '#A9D18E',
  manager: '#B4A7D6',
  witness: '#66bb6a',
  echo: '#b0bec5',
  lighthouse: '#f6c177',
  night_sailor: '#7aa2f7',
  old_letter: '#c0a36e',
  quiet_garden: '#7fcfa0',
  warm_palm: '#ff9aa2',
}

// Agent chat state
const chatOpen = ref(false)
const chatAgent = ref(null)
const chatMessages = ref([])
const chatInput = ref('')
const chatSending = ref(false)
const chatMessagesEl = ref(null)
const chatInputEl = ref(null)

function canOpenDialogue(user) {
  return Boolean(user?.can_chat)
}

function normalizeSimilarUsers(users) {
  return (users || []).map((u) => ({
    ...u,
    profile_kind: u?.profile_kind || 'peer',
    can_chat: canOpenDialogue(u),
    encouraged: false,
  }))
}

function personaLabel(personaType) {
  return personaLabelMap[personaType] || '匿名留声'
}

function personaLabelColor(personaType) {
  return personaColorMap[personaType] || '#b0bec5'
}

function applyTabFromQuery() {
  const raw = route.query?.tab
  const tab = raw === 'bottle' ? 'bottle' : raw === 'resonance' ? 'resonance' : ''
  if (tab) activeTab.value = tab
}

async function consumeRouteAction() {
  const action = route.query?.action
  if (action !== 'pick') return
  if (activeTab.value !== 'bottle') return

  if (bottlePicking.value) return
  if (pickedBottle.value) {
    const nextQuery = { ...route.query }
    delete nextQuery.action
    router.replace({ query: nextQuery })
    return
  }

  await nextTick()
  await pickBottle()

  // Remove the action param so back/refresh doesn't keep picking.
  const nextQuery = { ...route.query }
  delete nextQuery.action
  router.replace({ query: nextQuery })
}

onMounted(async () => {
  applyTabFromQuery()
  if (isShowcaseActive.value) {
    similarUsers.value = normalizeSimilarUsers(showcaseStore.socialData.similarUsers)
    myBottles.value = showcaseStore.socialData.myBottles || []
    pickedBottle.value = showcaseStore.socialData.pickedBottle || null
    await consumeRouteAction()
    return
  }
  await loadSimilarUsers()
  await loadMyBottles()
  await consumeRouteAction()
})

watch(
  () => showcaseStore.socialData,
  (payload) => {
    if (!isShowcaseActive.value) return
    similarUsers.value = normalizeSimilarUsers(payload.similarUsers)
    myBottles.value = payload.myBottles || []
    if (!pickedBottle.value) {
      pickedBottle.value = payload.pickedBottle || null
    }
  },
  { deep: true }
)

watch(isShowcaseActive, async (active) => {
  if (active) {
    similarUsers.value = normalizeSimilarUsers(showcaseStore.socialData.similarUsers)
    myBottles.value = showcaseStore.socialData.myBottles || []
    pickedBottle.value = showcaseStore.socialData.pickedBottle || null
    applyTabFromQuery()
    await consumeRouteAction()
    return
  }

  pickedBottle.value = null
  await loadSimilarUsers()
  await loadMyBottles()
  applyTabFromQuery()
  await consumeRouteAction()
})

watch(
  () => route.query,
  async () => {
    applyTabFromQuery()
    await consumeRouteAction()
  }
)

async function loadSimilarUsers() {
  if (isShowcaseActive.value) {
    similarUsers.value = normalizeSimilarUsers(showcaseStore.socialData.similarUsers)
    return
  }
  similarLoading.value = true
  try {
    const res = await axios.get(`${baseURL}/api/social/similarity`, { headers: authHeaders() })
    similarUsers.value = normalizeSimilarUsers(res.data.similar_users)
  } catch (e) {
    console.warn('Failed to load similar users:', e)
  } finally {
    similarLoading.value = false
  }
}

async function sendEncouragement(anonymousId) {
  const user = similarUsers.value.find(u => u.anonymous_id === anonymousId)
  if (user) user.encouraged = true
}

async function sendBottle() {
  if (!bottlePersona.value) return
  if (isShowcaseActive.value) {
    const demoAgentId = `bottle_demo_${Date.now()}`
    const demoAgent = {
      anonymous_id: demoAgentId,
      name: '阿梨',
      theme: '拾信',
      similarity: 0.88,
      shared_beliefs: ['你不必硬扛', '我会在'],
      exiles_summary: '我也曾把很多话藏在心里，后来才发现，说出来不等于脆弱。',
      firefighters_summary: '我会先陪你把情绪放稳，再一起看清它想保护什么。',
      can_chat: true,
      profile_kind: 'guide',
    }
    const msg = (bottleMessage.value || '').trim()
    const opening = msg
      ? `我捡到了你的漂流瓶。你写的那句「${msg.slice(0, 18)}」让我停了一下。要不要多说一点？`
      : '我捡到了你的漂流瓶。想说什么都可以，我在。'

    const mockBottle = {
      id: `demo_bottle_${Date.now()}`,
      persona_type: bottlePersona.value,
      status: 'drifting',
      created_at: new Date().toISOString(),
      message: bottleMessage.value || '',
    }
    myBottles.value = [mockBottle, ...(myBottles.value || [])].slice(0, 20)
    bottlePersona.value = null
    bottleMessage.value = ''

    openChat(demoAgent)
    if (!chatMessages.value.length && opening) {
      chatMessages.value.push({ role: 'agent', content: opening })
      saveChatHistory(demoAgentId, chatMessages.value)
      await nextTick()
      scrollChatToBottom()
    }
    window.$snackbar?.('有人捡起了你的漂流瓶，正在对话…', 'success')
    return
  }
  bottleSending.value = true
  try {
    const res = await axios.post(`${baseURL}/api/social/bottle/send`, {
      persona_type: bottlePersona.value,
      message: bottleMessage.value
    }, { headers: authHeaders() })

    const matchedAgent = res?.data?.matched_agent || null
    const opening = (res?.data?.opening_reply || '').trim()

    bottlePersona.value = null
    bottleMessage.value = ''
    await loadMyBottles()

    if (matchedAgent?.can_chat) {
      openChat(matchedAgent)
      if (!chatMessages.value.length && opening) {
        chatMessages.value.push({ role: 'agent', content: opening })
        saveChatHistory(matchedAgent.anonymous_id, chatMessages.value)
        await nextTick()
        scrollChatToBottom()
      }
      window.$snackbar?.('有人捡起了你的漂流瓶，正在对话…', 'success')
    } else {
      window.$snackbar?.('漂流瓶已投入大海', 'success')
    }
  } catch (e) {
    console.warn('Failed to send bottle:', e)
    window.$snackbar?.('投放失败，请稍后再试', 'error')
  } finally {
    bottleSending.value = false
  }
}

async function pickBottle() {
  if (isShowcaseActive.value) {
    pickedBottle.value = showcaseStore.socialData.pickedBottle || null
    return
  }
  bottlePicking.value = true
  try {
    const res = await axios.post(`${baseURL}/api/social/bottle/receive`, {}, { headers: authHeaders() })
    pickedBottle.value = res.data
  } catch (e) {
    console.warn('No bottles available:', e)
  } finally {
    bottlePicking.value = false
  }
}

async function loadMyBottles() {
  if (isShowcaseActive.value) {
    myBottles.value = showcaseStore.socialData.myBottles || []
    return
  }
  try {
    const res = await axios.get(`${baseURL}/api/social/bottles/mine`, { headers: authHeaders() })
    myBottles.value = res.data.bottles || []
  } catch {
    // ignore
  }
}

// --- Agent Chat Functions ---

function getChatStorageKey(agentId) {
  const uid = authStore.user?.id || 'anonymous'
  return `social_chat_u${uid}_${agentId}`
}

function loadChatHistory(agentId) {
  try {
    const raw = localStorage.getItem(getChatStorageKey(agentId))
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function saveChatHistory(agentId, messages) {
  localStorage.setItem(getChatStorageKey(agentId), JSON.stringify(messages))
}

function openChat(agent) {
  chatAgent.value = agent
  chatMessages.value = loadChatHistory(agent.anonymous_id)
  chatInput.value = ''
  chatOpen.value = true
  nextTick(() => scrollChatToBottom())
}

function closeChat() {
  chatOpen.value = false
  chatAgent.value = null
  chatMessages.value = []
  chatInput.value = ''
}

function scrollChatToBottom() {
  if (chatMessagesEl.value) {
    chatMessagesEl.value.scrollTop = chatMessagesEl.value.scrollHeight
  }
}

function autoResizeChatInput() {
  const el = chatInputEl.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 100) + 'px'
}

async function sendChatMessage() {
  const text = chatInput.value.trim()
  if (!text || chatSending.value || !chatAgent.value) return

  const agentId = chatAgent.value.anonymous_id
  chatMessages.value.push({ role: 'user', content: text })
  saveChatHistory(agentId, chatMessages.value)
  chatInput.value = ''
  chatSending.value = true

  if (chatInputEl.value) {
    chatInputEl.value.style.height = 'auto'
  }

  await nextTick()
  scrollChatToBottom()

  if (isShowcaseActive.value) {
    await new Promise(resolve => setTimeout(resolve, 650))
    const reply = showcaseStore.mockAgentReply(chatAgent.value, text)
    chatMessages.value.push({ role: 'agent', content: reply })
    saveChatHistory(agentId, chatMessages.value)
    chatSending.value = false
    await nextTick()
    scrollChatToBottom()
    return
  }

  try {
    if (chatAgent.value?.profile_kind !== 'guide') {
      chatMessages.value.push({ role: 'agent', content: '这位同行者暂不支持实时对话，你可以先发送匿名鼓励。' })
      saveChatHistory(agentId, chatMessages.value)
      return
    }

    const res = await axios.post(`${baseURL}/api/social/agent-chat`, {
      agent_id: agentId,
      message: text,
      history: chatMessages.value.filter(m => m.role !== undefined)
    }, { headers: authHeaders() })

    const reply = res.data.reply || res.data.message || '...'
    chatMessages.value.push({ role: 'agent', content: reply })
    saveChatHistory(agentId, chatMessages.value)
  } catch (e) {
    console.warn('Agent chat failed:', e)
    chatMessages.value.push({ role: 'agent', content: '抱歉，暂时无法回复，请稍后再试。' })
    saveChatHistory(agentId, chatMessages.value)
  } finally {
    chatSending.value = false
    await nextTick()
    scrollChatToBottom()
  }
}
</script>

<style scoped>
.social-root {
  position: fixed;
  inset: 0;
  overflow: hidden;
}
.social-scroll {
  position: relative;
  z-index: 10;
  height: 100vh;
  overflow-y: auto;
  padding: 24px 20px 60px;
  max-width: 560px;
  margin: 0 auto;
}
.social-header {
  text-align: center;
  margin-bottom: 24px;
  position: relative;
}
.back-btn {
  position: absolute;
  left: 0;
  top: 0;
  color: rgba(255,255,255,0.6) !important;
}
.social-title {
  font-size: 26px;
  font-weight: 700;
  color: white;
  letter-spacing: 2px;
}
.social-subtitle {
  font-size: 13px;
  color: rgba(255,255,255,0.5);
  margin-top: 4px;
}
.social-tabs {
  display: flex;
  justify-content: center;
  margin-bottom: 24px;
}
.social-tabs :deep(.v-btn) {
  color: rgba(255,255,255,0.6) !important;
  border-color: rgba(255,255,255,0.2) !important;
  font-size: 13px;
}
.social-tabs :deep(.v-btn--active) {
  background: rgba(255,255,255,0.12) !important;
  color: white !important;
}
.glass-card {
  background: rgba(255,255,255,0.06);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 12px;
  padding: 16px;
}
.loading-state, .empty-state {
  text-align: center;
  padding: 40px 0;
  color: rgba(255,255,255,0.5);
}
.sub-text {
  font-size: 12px;
  color: rgba(255,255,255,0.35);
  margin-top: 6px;
}
.similar-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.similar-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}
.similar-name {
  font-size: 14px;
  font-weight: 600;
  color: rgba(255,255,255,0.8);
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}
.name-text {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.kind-tag {
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 999px;
  color: rgba(255,255,255,0.92);
  border: 1px solid rgba(255,255,255,0.28);
  background: rgba(255,255,255,0.12);
}
.theme-tag {
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 999px;
  color: rgba(255,255,255,0.9);
  border: 1px solid rgba(255,255,255,0.18);
  background: rgba(255,255,255,0.08);
}
.similar-score {
  font-size: 12px;
  color: rgba(255,255,255,0.45);
}
.similar-beliefs {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 10px;
}
.belief-tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  background: rgba(255,255,255,0.08);
  color: rgba(255,255,255,0.6);
}
.portrait-line {
  font-size: 12px;
  color: rgba(255,255,255,0.55);
  line-height: 1.5;
  margin: 2px 0;
}
.bottle-section {
  margin-bottom: 24px;
}
.section-label {
  font-size: 15px;
  font-weight: 600;
  color: rgba(255,255,255,0.8);
  margin-bottom: 6px;
}
.section-desc {
  font-size: 12px;
  color: rgba(255,255,255,0.4);
  margin-bottom: 12px;
}
.bottle-persona-label {
  font-size: 13px;
  font-weight: 700;
  margin-bottom: 6px;
}
.bottle-portrait, .bottle-diary {
  font-size: 13px;
  color: rgba(255,255,255,0.6);
  line-height: 1.6;
  margin: 4px 0;
}
.bottle-msg {
  font-size: 13px;
  color: rgba(255,255,255,0.5);
  font-style: italic;
  margin-top: 8px;
}
.my-bottle {
  margin-bottom: 8px;
}
.bottle-status {
  font-size: 11px;
  color: rgba(255,255,255,0.4);
  margin-bottom: 4px;
}
:deep(.v-field__outline) {
  --v-field-border-opacity: 0.25;
}
:deep(.v-field--focused .v-field__outline) {
  --v-field-border-opacity: 0.5;
}
:deep(.v-field__input), :deep(.v-select__selection-text) {
  color: white !important;
}
:deep(.v-label) {
  color: rgba(255,255,255,0.5) !important;
}

/* Agent Chat Overlay */
.chat-overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}
.chat-panel {
  width: 100%;
  max-width: 500px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  background: rgba(30,30,40,0.85);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 16px;
  padding: 0;
  overflow: hidden;
}
.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid rgba(255,255,255,0.08);
}
.chat-header-info {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.chat-header-text {
  min-width: 0;
}
.chat-agent-name {
  font-size: 14px;
  font-weight: 600;
  color: rgba(255,255,255,0.85);
  display: flex;
  align-items: center;
  gap: 6px;
}
.chat-agent-theme {
  font-size: 11px;
  color: rgba(255,255,255,0.4);
  margin-top: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.chat-close-btn {
  color: rgba(255,255,255,0.5) !important;
  flex-shrink: 0;
}
.chat-portraits {
  padding: 10px 16px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 200px;
}
.chat-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(255,255,255,0.3);
  font-size: 13px;
}
.chat-msg {
  display: flex;
}
.chat-msg-user {
  justify-content: flex-end;
}
.chat-msg-agent {
  justify-content: flex-start;
}
.chat-bubble {
  max-width: 80%;
  padding: 10px 14px;
  border-radius: 14px;
  font-size: 13px;
  line-height: 1.6;
  word-break: break-word;
}
.bubble-user {
  background: rgba(255,255,255,0.18);
  color: rgba(255,255,255,0.9);
  border-bottom-right-radius: 4px;
}
.bubble-agent {
  background: rgba(255,255,255,0.08);
  color: rgba(255,255,255,0.8);
  border-bottom-left-radius: 4px;
}
.chat-typing {
  display: flex;
  align-items: center;
  color: rgba(255,255,255,0.5);
  font-size: 12px;
}
.chat-input-area {
  padding: 12px 16px;
  border-top: 1px solid rgba(255,255,255,0.08);
}
.chat-input-wrap {
  display: flex;
  align-items: flex-end;
  gap: 4px;
}
.glass-input {
  background: rgba(255,255,255,0.1);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid rgba(255,255,255,0.18);
  border-radius: 22px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.05);
  transition: all 0.3s ease;
  padding: 6px 6px 6px 16px;
}
.chat-input-wrap:focus-within {
  background: rgba(255,255,255,0.14);
  border-color: rgba(255,255,255,0.3);
  box-shadow: 0 8px 24px rgba(0,0,0,0.1);
}
.chat-input-wrap textarea {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  color: white;
  font-size: 14px;
  line-height: 1.5;
  resize: none;
  max-height: 100px;
  padding: 6px 0;
}
.chat-input-wrap textarea::placeholder {
  color: rgba(255,255,255,0.35);
}
.chat-send-btn {
  color: rgba(255,255,255,0.6) !important;
  flex-shrink: 0;
}
.chat-send-btn:hover {
  color: white !important;
}
</style>
