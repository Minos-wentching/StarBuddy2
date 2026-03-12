<template>
  <div class="report-root">
    <ShaderBackground role="counselor" :intensity="0.2" />

    <div class="report-scroll">
      <!-- Header -->
      <div class="report-header">
        <v-btn icon variant="text" size="small" @click="$router.back()" class="back-btn">
          <v-icon>mdi-arrow-left</v-icon>
        </v-btn>
        <h1 class="report-title">成长报告</h1>
        <p class="report-subtitle">你的内心星图</p>
      </div>

      <div v-if="loading" class="report-loading">
        <v-progress-circular indeterminate color="white" size="32" />
        <span class="ml-3" style="color:rgba(255,255,255,0.6)">正在生成报告…</span>
      </div>

      <template v-else>
        <!-- Section 1: Core Beliefs -->
        <section class="report-section" v-if="coreBeliefs.length">
          <h2 class="section-title">
            <v-icon class="mr-2" size="20">mdi-map-marker-radius</v-icon>
            核心行为模式
          </h2>
          <div class="beliefs-grid">
            <div
              v-for="b in coreBeliefs" :key="b.belief_id"
              class="belief-card"
              :class="b.valence >= 0 ? 'belief-positive' : 'belief-negative'"
            >
              <div class="belief-content">{{ b.content }}</div>
              <div class="belief-meta">
                <span class="belief-intensity">强度 {{ b.intensity.toFixed(1) }}</span>
                <span v-if="b.origin_event" class="belief-origin">{{ b.origin_event }}</span>
              </div>
            </div>
          </div>
        </section>

        <!-- Section 2: Persona Portraits -->
        <section class="report-section" v-if="personaPortraits.exiles || personaPortraits.firefighters">
          <h2 class="section-title">
            <v-icon class="mr-2" size="20">mdi-account-heart</v-icon>
            伙伴画像
          </h2>
          <div class="portraits-grid">
            <div class="portrait-card" v-if="personaPortraits.exiles">
              <div class="portrait-label" style="color:#F4B183">感知精灵</div>
              <p class="portrait-text">{{ personaPortraits.exiles }}</p>
            </div>
            <div class="portrait-card" v-if="personaPortraits.firefighters">
              <div class="portrait-label" style="color:#A9D18E">规则守卫</div>
              <p class="portrait-text">{{ personaPortraits.firefighters }}</p>
            </div>
          </div>
        </section>

        <!-- Section 3: Council Review -->
        <section class="report-section" v-if="councilSummary">
          <h2 class="section-title">
            <v-icon class="mr-2" size="20">mdi-account-group</v-icon>
            会议回顾
          </h2>
          <div class="council-summary glass-card">
            <p>{{ councilSummary }}</p>
          </div>
        </section>

        <!-- Section 4: Growth Metrics -->
        <section class="report-section" v-if="emotionTrend.length">
          <h2 class="section-title">
            <v-icon class="mr-2" size="20">mdi-chart-line</v-icon>
            成长轨迹
          </h2>
          <div class="metrics-row">
            <div class="metric-card glass-card">
              <div class="metric-label">情绪强度变化</div>
              <div class="metric-sparkline">
                <svg viewBox="0 0 200 40" class="sparkline-svg">
                  <polyline
                    :points="sparklinePoints"
                    fill="none"
                    stroke="rgba(255,255,255,0.6)"
                    stroke-width="2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                  />
                </svg>
              </div>
            </div>
            <div class="metric-card glass-card" v-if="selfPresence">
              <div class="metric-label">Self 在场感</div>
              <div class="metric-value">{{ (selfPresence * 100).toFixed(0) }}%</div>
              <div class="metric-sub">{{ selfPresenceTrend }}</div>
            </div>
          </div>
        </section>

        <!-- Section 5: Counselor Note -->
        <section class="report-section" v-if="counselorNote">
          <h2 class="section-title">
            <v-icon class="mr-2" size="20">mdi-heart-pulse</v-icon>
            星星向导寄语
          </h2>
          <div class="counselor-note glass-card">
            <p>{{ counselorNote }}</p>
          </div>
        </section>

        <!-- Empty state -->
        <div v-if="isEmpty" class="report-empty">
          <v-icon size="48" style="color:rgba(255,255,255,0.3)">mdi-file-document-outline</v-icon>
          <p>还没有足够的数据生成报告</p>
          <p class="text-caption" style="color:rgba(255,255,255,0.4)">继续对话探索，报告会自动丰富</p>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { usePersonaStore } from '@/stores/persona'
import { useShowcaseStore } from '@/stores/showcase'
import { dialogueApi } from '@/api/dialogue'
import ShaderBackground from '@/components/ShaderBackground.vue'

const personaStore = usePersonaStore()
const showcaseStore = useShowcaseStore()

const loading = ref(true)
const coreBeliefs = ref([])
const personaPortraits = ref({})
const councilSummary = ref('')
const emotionTrend = ref([])
const selfPresence = ref(null)
const selfPresenceTrend = ref('')
const counselorNote = ref('')

const isEmpty = computed(() =>
  !coreBeliefs.value.length &&
  !personaPortraits.value.exiles &&
  !personaPortraits.value.firefighters &&
  !councilSummary.value &&
  !counselorNote.value
)

const sparklinePoints = computed(() => {
  if (!emotionTrend.value.length) return ''
  const max = Math.max(...emotionTrend.value, 1)
  return emotionTrend.value.map((v, i) => {
    const x = (i / Math.max(emotionTrend.value.length - 1, 1)) * 200
    const y = 40 - (v / max) * 36
    return `${x},${y}`
  }).join(' ')
})

const applyReportPayload = (payload = {}) => {
  coreBeliefs.value = payload.core_beliefs || []
  personaPortraits.value = payload.persona_portraits || {}
  councilSummary.value = payload.council_summary || ''
  emotionTrend.value = payload.emotion_trend || []
  selfPresence.value = payload.self_presence
  selfPresenceTrend.value = payload.self_presence_trend || ''
  counselorNote.value = payload.counselor_note || ''
}

onMounted(async () => {
  const loadLiveReport = async () => {
    // Try backend report endpoint first
    const sessionId = localStorage.getItem('current_session_id')
    if (sessionId) {
      try {
        const res = await dialogueApi.getReport(sessionId)
        applyReportPayload(res.data)
        return
      } catch {
        // Fallback to local store data
      }
    }

    // Fallback: use local store data
    coreBeliefs.value = personaStore.coreBeliefs || []
    councilSummary.value = personaStore.councilConclusion || ''
    emotionTrend.value = (personaStore.personaHistory || []).map(h => h.intensity ?? 0)
    selfPresence.value = personaStore.selfPresenceClarity
    selfPresenceTrend.value = personaStore.selfPresenceTrend === 'improving'
      ? '持续提升中'
      : personaStore.selfPresenceTrend === 'declining'
        ? '有所波动'
        : '保持稳定'
    counselorNote.value = personaStore.selfPresenceAnalysis || ''
  }

  try {
    if (showcaseStore.active) {
      applyReportPayload(showcaseStore.reportData)
      return
    }
    await loadLiveReport()
  } finally {
    loading.value = false
  }

  watch(
    () => showcaseStore.active,
    async (active) => {
      if (active) {
        applyReportPayload(showcaseStore.reportData)
        loading.value = false
        return
      }

      loading.value = true
      try {
        await loadLiveReport()
      } finally {
        loading.value = false
      }
    }
  )
})

watch(
  () => showcaseStore.reportData,
  (payload) => {
    if (!showcaseStore.active) return
    applyReportPayload(payload)
  },
  { deep: true }
)
</script>

<style scoped>
.report-root {
  position: fixed;
  inset: 0;
  overflow: hidden;
}
.report-scroll {
  position: relative;
  z-index: 10;
  height: 100vh;
  overflow-y: auto;
  padding: 24px 20px 60px;
  max-width: 600px;
  margin: 0 auto;
}
.report-header {
  text-align: center;
  margin-bottom: 32px;
  position: relative;
}
.back-btn {
  position: absolute;
  left: 0;
  top: 0;
  color: rgba(255,255,255,0.6) !important;
}
.report-title {
  font-size: 28px;
  font-weight: 700;
  color: white;
  letter-spacing: 2px;
}
.report-subtitle {
  font-size: 14px;
  color: rgba(255,255,255,0.5);
  margin-top: 4px;
}
.report-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 60px 0;
}
.report-section {
  margin-bottom: 28px;
}
.section-title {
  font-size: 16px;
  font-weight: 600;
  color: rgba(255,255,255,0.85);
  margin-bottom: 14px;
  display: flex;
  align-items: center;
}
.glass-card {
  background: rgba(255,255,255,0.06);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 12px;
  padding: 16px;
}

/* Beliefs */
.beliefs-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.belief-card {
  flex: 1 1 calc(50% - 5px);
  min-width: 140px;
  border-radius: 12px;
  padding: 14px;
  border: 1px solid;
}
.belief-positive {
  background: rgba(255,183,77,0.1);
  border-color: rgba(255,183,77,0.25);
}
.belief-negative {
  background: rgba(100,181,246,0.1);
  border-color: rgba(100,181,246,0.25);
}
.belief-content {
  font-size: 14px;
  color: rgba(255,255,255,0.85);
  margin-bottom: 8px;
  line-height: 1.5;
}
.belief-meta {
  display: flex;
  gap: 8px;
  font-size: 11px;
  color: rgba(255,255,255,0.45);
}

/* Portraits */
.portraits-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.portrait-card {
  background: rgba(255,255,255,0.06);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 12px;
  padding: 16px;
}
.portrait-label {
  font-size: 13px;
  font-weight: 700;
  margin-bottom: 8px;
}
.portrait-text {
  font-size: 13px;
  color: rgba(255,255,255,0.7);
  line-height: 1.6;
  margin: 0;
}

/* Council summary */
.council-summary p {
  font-size: 13px;
  color: rgba(255,255,255,0.7);
  line-height: 1.7;
  margin: 0;
}

/* Metrics */
.metrics-row {
  display: flex;
  gap: 12px;
}
.metric-card {
  flex: 1;
}
.metric-label {
  font-size: 12px;
  color: rgba(255,255,255,0.5);
  margin-bottom: 8px;
}
.metric-value {
  font-size: 28px;
  font-weight: 700;
  color: white;
}
.metric-sub {
  font-size: 11px;
  color: rgba(255,255,255,0.4);
  margin-top: 4px;
}
.sparkline-svg {
  width: 100%;
  height: 40px;
}

/* Counselor note */
.counselor-note p {
  font-size: 14px;
  color: rgba(255,255,255,0.75);
  line-height: 1.7;
  margin: 0;
  font-style: italic;
}

/* Empty */
.report-empty {
  text-align: center;
  padding: 60px 0;
  color: rgba(255,255,255,0.5);
}
.report-empty p {
  margin-top: 12px;
}
</style>
