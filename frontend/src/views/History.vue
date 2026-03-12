<template>
  <div class="history-root">
    <ShaderBackground role="manager" :intensity="0.15" />

    <div class="scroll-container">
      <!-- 标题栏 -->
      <div class="title-bar">
        <v-btn
          icon
          variant="text"
          size="small"
          class="back-btn"
          @click="$router.push('/')"
        >
          <v-icon color="rgba(255,255,255,0.6)">mdi-arrow-left</v-icon>
        </v-btn>
        <div class="page-title">历史版本</div>
        <v-btn
          icon
          variant="text"
          size="small"
          class="refresh-btn"
          @click="refreshSnapshots"
        >
          <v-icon color="rgba(255,255,255,0.6)">mdi-refresh</v-icon>
        </v-btn>
      </div>

      <p class="page-subtitle">查看和管理状态版本快照</p>

      <!-- 伙伴固定形象 -->
      <div class="glass-card" style="margin-bottom: 16px;">
        <div class="d-flex align-center justify-space-between" style="margin-bottom: 12px;">
          <div class="section-label">伙伴固定形象</div>
          <div class="d-flex align-center" style="gap: 8px;">
            <v-chip size="x-small" class="dark-chip">v{{ onboardingProfileVersion }}</v-chip>
            <v-chip
              size="x-small"
              :class="['dark-chip', profileConfirmed ? 'chip-success' : 'chip-warning']"
            >
              {{ profileConfirmed ? '已确认' : '待确认' }}
            </v-chip>
          </div>
        </div>
        <div class="portrait-card exiles">
          <div class="portrait-label">感知精灵</div>
          <div class="portrait-text">{{ exilesPortrait }}</div>
        </div>
        <div class="portrait-card firefighters" style="margin-top: 10px;">
          <div class="portrait-label">规则守卫</div>
          <div class="portrait-text">{{ firefightersPortrait }}</div>
        </div>
      </div>

      <!-- 过滤栏 -->
      <div class="glass-card" style="margin-bottom: 20px;">
        <v-select
          v-model="filters.persona"
          label="伙伴"
          :items="personaOptions"
          clearable
          prepend-icon="mdi-account"
          density="compact"
          color="white"
          base-color="rgba(255,255,255,0.4)"
          class="dark-field"
          @update:model-value="loadSnapshots"
        ></v-select>
        <v-text-field
          v-model="filters.minIntensity"
          label="最小情绪强度"
          type="number"
          min="0"
          max="1"
          step="0.1"
          clearable
          prepend-icon="mdi-emoticon-outline"
          density="compact"
          color="white"
          base-color="rgba(255,255,255,0.4)"
          class="dark-field"
        ></v-text-field>
        <v-text-field
          v-model="filters.maxIntensity"
          label="最大情绪强度"
          type="number"
          min="0"
          max="1"
          step="0.1"
          clearable
          prepend-icon="mdi-emoticon-outline"
          density="compact"
          color="white"
          base-color="rgba(255,255,255,0.4)"
          class="dark-field"
        ></v-text-field>
        <v-text-field
          v-model="filters.tags"
          label="标签（逗号分隔）"
          clearable
          prepend-icon="mdi-tag"
          density="compact"
          color="white"
          base-color="rgba(255,255,255,0.4)"
          class="dark-field"
          hide-details
        ></v-text-field>
      </div>

      <!-- 加载状态 -->
      <v-progress-linear
        v-if="loading"
        indeterminate
        color="rgba(255,255,255,0.5)"
        style="margin-bottom: 16px; border-radius: 4px;"
      ></v-progress-linear>

      <!-- 空状态 -->
      <div v-if="!loading && snapshots.length === 0" class="glass-card empty-state">
        <v-icon size="64" color="rgba(255,255,255,0.2)" style="margin-bottom: 16px;">mdi-history</v-icon>
        <div class="empty-title">暂无版本快照</div>
        <p class="body-text" style="margin-bottom: 16px;">开始你的第一次对话，系统会自动创建心理状态快照</p>
        <v-btn variant="flat" size="small" color="rgba(255,255,255,0.12)" style="color: white;" to="/">开始对话</v-btn>
      </div>

      <!-- 快照列表 -->
      <template v-if="snapshots.length > 0">
        <div class="snapshot-count body-text" style="margin-bottom: 12px;">
          共 {{ snapshots.length }} 个快照
        </div>

        <div
          v-for="snapshot in snapshots"
          :key="snapshot.id"
          class="glass-card snapshot-item"
          :class="snapshot.persona"
          @click="$router.push(`/history/${snapshot.id}`)"
        >
          <div class="d-flex align-center" style="gap: 12px;">
            <v-avatar :color="getPersonaColor(snapshot.persona)" size="40">
              <v-icon size="20" color="white">{{ getPersonaIcon(snapshot.persona) }}</v-icon>
            </v-avatar>
            <div style="flex: 1; min-width: 0;">
              <div class="d-flex align-center" style="gap: 8px; margin-bottom: 4px;">
                <span class="snapshot-persona">{{ formatPersona(snapshot.persona) }}</span>
                <v-chip size="x-small" class="dark-chip">
                  {{ (snapshot.emotion_intensity * 100).toFixed(0) }}%
                </v-chip>
              </div>
              <div class="d-flex align-center body-text" style="font-size: 12px; gap: 10px;">
                <span class="d-flex align-center" style="gap: 3px;">
                  <v-icon size="12" color="rgba(255,255,255,0.4)">mdi-clock-outline</v-icon>
                  {{ formatDate(snapshot.created_at) }}
                </span>
                <span class="d-flex align-center" style="gap: 3px;">
                  <v-icon size="12" color="rgba(255,255,255,0.4)">mdi-message-text</v-icon>
                  {{ snapshot.message_count }} 条消息
                </span>
              </div>
              <div v-if="snapshot.tags && snapshot.tags.length" style="margin-top: 6px;">
                <v-chip
                  v-for="tag in snapshot.tags"
                  :key="tag"
                  size="x-small"
                  class="dark-chip"
                  style="margin-right: 4px; margin-bottom: 4px;"
                >
                  {{ tag }}
                </v-chip>
              </div>
            </div>
            <v-btn
              icon
              variant="text"
              size="small"
              @click.stop="restoreSnapshot(snapshot.session_id, snapshot.id)"
              :loading="restoring === snapshot.id"
            >
              <v-icon color="rgba(255,255,255,0.5)" size="20">mdi-restore</v-icon>
              <v-tooltip activator="parent" location="top">恢复到此版本</v-tooltip>
            </v-btn>
          </div>
        </div>
      </template>

      <!-- 分页 -->
      <div v-if="snapshots.length > 0" class="pagination-wrap">
        <v-pagination
          v-model="page"
          :length="Math.ceil(total / pageSize)"
          :total-visible="5"
          density="compact"
          @update:model-value="loadSnapshots"
        ></v-pagination>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { versionApi } from '@/api/version'
import { useAuthStore } from '@/stores/auth'
import { useDialogueStore } from '@/stores/dialogue'
import { getPersonaDisplay as getPersonaDisplayUtil, getPersonaIcon, getPersonaColor, getEmotionColorName } from '@/composables/usePersona'
import ShaderBackground from '@/components/ShaderBackground.vue'

const authStore = useAuthStore()
const dialogueStore = useDialogueStore()

const snapshots = ref([])
const loading = ref(false)
const restoring = ref(null)
const total = ref(0)
const page = ref(1)
const pageSize = 10

const filters = ref({
  persona: '',
  minIntensity: null,
  maxIntensity: null,
  tags: ''
})

let debounceTimer = null
watch(
  () => [filters.value.minIntensity, filters.value.maxIntensity, filters.value.tags],
  () => {
    clearTimeout(debounceTimer)
    debounceTimer = setTimeout(() => {
      page.value = 1
      loadSnapshots()
    }, 400)
  }
)

const personaOptions = [
  { title: '安全岛', value: 'manager' },
  { title: '感知精灵', value: 'exiles' },
  { title: '规则守卫', value: 'firefighters' },
  { title: '星星向导', value: 'healer' }
]

const currentSessionId = computed(() => {
  return dialogueStore.currentSession?.id || localStorage.getItem('current_session_id')
})

const onboardingProfile = computed(() => authStore.user?.settings?.ifs_onboarding || {})
const onboardingProfileVersion = computed(() => Number(onboardingProfile.value?.profile_version || 1))
const profileConfirmed = computed(() => Boolean(onboardingProfile.value?.profile_confirmed))
const exilesPortrait = computed(() =>
  onboardingProfile.value?.persona_portraits?.exiles || '问卷完成后将生成并固定在此。'
)
const firefightersPortrait = computed(() =>
  onboardingProfile.value?.persona_portraits?.firefighters || '问卷完成后将生成并固定在此。'
)

const loadSnapshots = async () => {
  if (!currentSessionId.value) {
    window.$snackbar('请先创建或选择会话', 'warning')
    return
  }
  loading.value = true
  try {
    const params = { limit: pageSize, offset: (page.value - 1) * pageSize }
    if (filters.value.persona) params.persona = filters.value.persona
    if (filters.value.minIntensity !== null) params.min_intensity = parseFloat(filters.value.minIntensity)
    if (filters.value.maxIntensity !== null) params.max_intensity = parseFloat(filters.value.maxIntensity)
    if (filters.value.tags) params.tags = filters.value.tags
    const response = await versionApi.listSnapshots(currentSessionId.value, params)
    snapshots.value = response.data.snapshots || []
    total.value = response.data.total || snapshots.value.length
  } catch (error) {
    console.error('加载快照失败:', error)
    snapshots.value = []
  } finally {
    loading.value = false
  }
}

const refreshSnapshots = () => { page.value = 1; loadSnapshots() }

const restoreSnapshot = async (sessionId, snapshotId) => {
  if (!confirm('确定要恢复到此版本吗？当前状态将被覆盖。')) return
  restoring.value = snapshotId
  try {
    await versionApi.restoreSnapshot(sessionId, snapshotId)
  } catch (error) {
    console.error('恢复快照失败:', error)
  } finally {
    restoring.value = null
  }
}

const formatDate = (dateString) => {
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN', { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

const formatPersona = (persona) => getPersonaDisplayUtil(persona)

onMounted(() => { loadSnapshots() })
</script>

<style scoped>
.history-root {
  position: fixed;
  inset: 0;
  overflow: hidden;
}
.scroll-container {
  max-width: 600px;
  margin: 0 auto;
  padding: 24px 20px 60px;
  height: 100vh;
  overflow-y: auto;
  position: relative;
  z-index: 10;
}
.title-bar {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 4px;
}
.back-btn { position: absolute; left: 0; }
.refresh-btn { position: absolute; right: 0; }
.page-title {
  font-size: 28px;
  font-weight: 700;
  color: white;
  letter-spacing: 2px;
  text-align: center;
}
.page-subtitle {
  text-align: center;
  color: rgba(255,255,255,0.45);
  font-size: 13px;
  margin-bottom: 20px;
}
.glass-card {
  background: rgba(255,255,255,0.06);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 12px;
  padding: 16px;
}
.section-label {
  font-size: 13px;
  font-weight: 600;
  color: rgba(255,255,255,0.7);
}
.portrait-card {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 8px;
  padding: 10px 12px;
}
.portrait-card.exiles { border-left: 3px solid rgba(244,177,131,0.8); }
.portrait-card.firefighters { border-left: 3px solid rgba(169,209,142,0.8); }
.portrait-label {
  font-size: 11px;
  font-weight: 700;
  color: rgba(255,255,255,0.5);
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 4px;
}
.portrait-text {
  font-size: 13px;
  color: rgba(255,255,255,0.7);
  line-height: 1.5;
}
.body-text { color: rgba(255,255,255,0.7); }
.empty-state { text-align: center; padding: 48px 24px; }
.empty-title {
  font-size: 16px;
  font-weight: 600;
  color: rgba(255,255,255,0.5);
  margin-bottom: 8px;
}
.snapshot-count { font-size: 13px; font-weight: 600; }
.snapshot-item {
  margin-bottom: 10px;
  cursor: pointer;
  transition: background 0.2s;
}
.snapshot-item:hover { background: rgba(255,255,255,0.1); }
.snapshot-item.exiles { border-left: 3px solid rgba(244,177,131,0.8); }
.snapshot-item.firefighters { border-left: 3px solid rgba(169,209,142,0.8); }
.snapshot-item.manager { border-left: 3px solid rgba(91,155,213,0.7); }
.snapshot-item.healer, .snapshot-item.counselor { border-left: 3px solid rgba(180,167,214,0.7); }
.snapshot-persona {
  font-size: 14px;
  font-weight: 600;
  color: rgba(255,255,255,0.9);
}
.dark-chip {
  background: rgba(255,255,255,0.1) !important;
  color: rgba(255,255,255,0.7) !important;
  border: 1px solid rgba(255,255,255,0.08) !important;
}
.dark-chip.chip-success {
  background: rgba(76,175,80,0.2) !important;
  color: rgba(130,230,140,0.9) !important;
}
.dark-chip.chip-warning {
  background: rgba(255,180,50,0.15) !important;
  color: rgba(255,200,100,0.9) !important;
}
.dark-field :deep(.v-field) { color: rgba(255,255,255,0.8); }
.dark-field :deep(.v-field__outline) { --v-field-border-opacity: 0.15; }
.dark-field :deep(.v-label) { color: rgba(255,255,255,0.4); }
.dark-field :deep(.v-icon) { color: rgba(255,255,255,0.35); }
.dark-field :deep(input) { color: rgba(255,255,255,0.85); }
.pagination-wrap {
  display: flex;
  justify-content: center;
  margin-top: 20px;
  padding-bottom: 20px;
}
.pagination-wrap :deep(.v-pagination__item) {
  background: rgba(255,255,255,0.06) !important;
  color: rgba(255,255,255,0.6) !important;
  border: 1px solid rgba(255,255,255,0.08);
}
.pagination-wrap :deep(.v-pagination__item--is-active) {
  background: rgba(255,255,255,0.18) !important;
  color: white !important;
}
.pagination-wrap :deep(.v-btn) { color: rgba(255,255,255,0.5); }
</style>
