<template>
  <div class="immersive-root">
    <ShaderBackground :role="personaStore.currentPersona" :intensity="personaStore.emotionIntensity" />

    <!-- Top bar -->
    <div class="immersive-topbar">
      <v-btn icon variant="text" size="small" @click="$router.back()" style="color:rgba(255,255,255,0.6)">
        <v-icon>mdi-arrow-left</v-icon>
      </v-btn>
      <div class="mode-toggle">
        <v-btn-toggle v-model="viewMode" mandatory density="compact" variant="outlined" color="white">
          <v-btn value="timeline" size="small" class="text-none">时间线</v-btn>
          <v-btn value="story" size="small" class="text-none">故事模式</v-btn>
        </v-btn-toggle>
      </div>
    </div>

    <!-- Timeline mode -->
    <div v-if="viewMode === 'timeline'" class="immersive-content">
      <div v-if="!nodes.length" class="empty-hint">
        <p>空白视图。开始一段对话后回到此页体验沉浸式叙事。</p>
        <p class="sub-hint">提示：此视图一次只呈现一个节点。点击卡片以推进。</p>
      </div>
      <div v-else class="timeline-scroll">
        <NarrativeCard
          v-if="currentText"
          :text="currentText"
          :role="personaStore.currentPersona"
          @next="goNext"
        />
        <div class="timeline-nav">
          <v-btn icon variant="text" size="small" :disabled="currentIndex <= 0" @click="currentIndex--" style="color:rgba(255,255,255,0.5)">
            <v-icon>mdi-chevron-left</v-icon>
          </v-btn>
          <span class="timeline-counter">{{ currentIndex + 1 }} / {{ nodes.length }}</span>
          <v-btn icon variant="text" size="small" :disabled="currentIndex >= nodes.length - 1" @click="currentIndex++" style="color:rgba(255,255,255,0.5)">
            <v-icon>mdi-chevron-right</v-icon>
          </v-btn>
        </div>
      </div>
    </div>

    <!-- Story mode -->
    <div v-else class="immersive-content">
      <div v-if="storyLoading" class="story-loading">
        <v-progress-circular indeterminate color="white" size="28" />
        <span class="ml-3" style="color:rgba(255,255,255,0.6)">正在编织你的故事…</span>
      </div>
      <div v-else-if="!storyChapters.length" class="empty-hint">
        <p>还没有足够的对话来生成故事</p>
        <p class="sub-hint">继续探索后再来看看吧</p>
      </div>
      <div v-else class="story-scroll">
        <div v-for="(ch, i) in storyChapters" :key="i" class="story-chapter">
          <div class="chapter-num">第 {{ i + 1 }} 章</div>
          <h3 class="chapter-title">{{ ch.title }}</h3>
          <img v-if="ch.image_url" :src="ch.image_url" class="chapter-image" alt="" />
          <p class="chapter-content">{{ ch.content }}</p>
        </div>
      </div>
    </div>

    <!-- Bottom HUD -->
    <div class="immersive-hud">
      <span class="hud-chip">安全岛</span>
      <span class="hud-chip">感知精灵</span>
      <span class="hud-chip">规则守卫</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useDialogueStore } from '@/stores/dialogue'
import { usePersonaStore } from '@/stores/persona'
import { useShowcaseStore } from '@/stores/showcase'
import { dialogueApi } from '@/api/dialogue'
import ShaderBackground from '@/components/ShaderBackground.vue'
import NarrativeCard from '@/components/NarrativeCard.vue'

const dialogueStore = useDialogueStore()
const personaStore = usePersonaStore()
const showcaseStore = useShowcaseStore()

const viewMode = ref('timeline')
const currentIndex = ref(0)
const storyLoading = ref(false)
const storyChapters = ref([])
const isShowcaseActive = computed(() => showcaseStore.active)

const nodes = computed(() => {
  const sourceMessages = isShowcaseActive.value
    ? showcaseStore.demoMessages
    : dialogueStore.getConversationHistory(true)

  return sourceMessages.map(m => {
    const labelMap = { manager: '安全岛', exiles: '感知精灵', firefighters: '规则守卫', counselor: '星星向导' }
    const prefix = m.type === 'user' ? '你：' : (m.persona ? `${labelMap[m.persona] || m.persona}：` : '')
    return `${prefix}${m.content || m.message || ''}`
  })
})

const currentText = computed(() => nodes.value[currentIndex.value] || '')

// Reset index when nodes change
watch(nodes, (val) => {
  if (val.length) currentIndex.value = val.length - 1
}, { immediate: true })

function goNext() {
  if (currentIndex.value < nodes.value.length - 1) {
    currentIndex.value++
  }
}

// Load story when switching to story mode
watch(viewMode, async (mode) => {
  if (mode === 'story' && !storyChapters.value.length) {
    if (isShowcaseActive.value) {
      storyChapters.value = [...showcaseStore.narrativeChapters]
      return
    }
    storyLoading.value = true
    try {
      const sessionId = localStorage.getItem('current_session_id')
      if (sessionId) {
        const res = await dialogueApi.getNarrative(sessionId)
        storyChapters.value = res.data.chapters || []
      }
    } catch (e) {
      console.warn('Failed to load narrative:', e)
    } finally {
      storyLoading.value = false
    }
  }
})

watch(
  () => showcaseStore.narrativeChapters,
  (chapters) => {
    if (!isShowcaseActive.value) return
    storyChapters.value = [...chapters]
  },
  { deep: true }
)

watch(isShowcaseActive, (active) => {
  if (!active) {
    storyChapters.value = []
  }
})
</script>

<style scoped>
.immersive-root {
  position: fixed;
  inset: 0;
  background: radial-gradient(1200px circle at 50% 30%, #0b0b12, #050508 60%, #000 100%);
  overflow: hidden;
}
.immersive-topbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
}
.mode-toggle :deep(.v-btn) {
  color: rgba(255,255,255,0.6) !important;
  border-color: rgba(255,255,255,0.2) !important;
  font-size: 12px;
}
.mode-toggle :deep(.v-btn--active) {
  background: rgba(255,255,255,0.12) !important;
  color: white !important;
}
.immersive-content {
  position: absolute;
  inset: 56px 0 48px 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 10;
  overflow-y: auto;
  padding: 20px;
}
.empty-hint {
  text-align: center;
  color: rgba(255,255,255,0.5);
  font-size: 15px;
  max-width: 400px;
}
.sub-hint {
  margin-top: 8px;
  font-size: 13px;
  opacity: 0.6;
}

/* Timeline */
.timeline-scroll {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  width: 100%;
  max-width: 600px;
}
.timeline-nav {
  display: flex;
  align-items: center;
  gap: 12px;
}
.timeline-counter {
  font-size: 12px;
  color: rgba(255,255,255,0.4);
  min-width: 60px;
  text-align: center;
}

/* Story mode */
.story-loading {
  display: flex;
  align-items: center;
}
.story-scroll {
  width: 100%;
  max-width: 560px;
  display: flex;
  flex-direction: column;
  gap: 32px;
}
.story-chapter {
  background: rgba(255,255,255,0.04);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 14px;
  padding: 24px 20px;
}
.chapter-num {
  font-size: 11px;
  color: rgba(255,255,255,0.35);
  text-transform: uppercase;
  letter-spacing: 2px;
  margin-bottom: 6px;
}
.chapter-title {
  font-size: 18px;
  font-weight: 600;
  color: rgba(255,255,255,0.85);
  margin-bottom: 14px;
}
.chapter-image {
  width: 100%;
  border-radius: 10px;
  margin-bottom: 14px;
  opacity: 0.85;
}
.chapter-content {
  font-size: 14px;
  color: rgba(255,255,255,0.65);
  line-height: 1.8;
  margin: 0;
}

/* Bottom HUD */
.immersive-hud {
  position: fixed;
  left: 16px;
  bottom: 12px;
  z-index: 20;
  display: flex;
  gap: 6px;
  opacity: 0.35;
  transition: opacity 0.3s;
}
.immersive-hud:hover {
  opacity: 0.75;
}
.hud-chip {
  font-size: 11px;
  padding: 3px 10px;
  border-radius: 20px;
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.12);
  color: rgba(255,255,255,0.6);
}
</style>
