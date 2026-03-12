<template>
  <v-container class="pa-4">
    <!-- 标题和导航 -->
    <div class="d-flex align-center mb-6">
      <v-icon size="36" color="primary" class="mr-3">mdi-account-group</v-icon>
      <div>
        <h1 class="text-h4">星球会议</h1>
        <p class="text-body-2 text-medium-emphasis">感知精灵与规则守卫的对话空间，星星向导提供整合视角</p>
      </div>
      <v-spacer></v-spacer>
      <v-btn color="primary" variant="tonal" @click="$router.push('/')" prepend-icon="mdi-message-text">
        返回对话
      </v-btn>
    </div>

    <!-- 议会状态卡片 -->
    <v-card class="mb-6" variant="outlined">
      <v-card-title class="d-flex align-center">
        <v-icon class="mr-2" :color="personaStore.isInnerCouncilActive ? 'info' : 'success'">
          {{ personaStore.isInnerCouncilActive ? 'mdi-loading mdi-spin' : 'mdi-check-circle' }}
        </v-icon>
        议会状态
      </v-card-title>
      <v-card-text>
        <div class="d-flex align-center">
          <div class="flex-grow-1">
            <div v-if="personaStore.isInnerCouncilActive" class="d-flex align-center">
              <v-progress-circular indeterminate size="20" width="2" class="mr-3" color="info"></v-progress-circular>
              <div>
                <div class="text-subtitle-1 font-weight-bold">会议进行中</div>
                <div class="text-body-2 text-medium-emphasis">
                  第 {{ personaStore.councilProgress.currentRound }} 轮 / 共 {{ personaStore.councilProgress.totalRounds }} 轮
                </div>
                <div v-if="personaStore.councilProgress.arguments.exiles || personaStore.councilProgress.arguments.firefighters" class="mt-2">
                  <div class="text-caption">当前对话焦点:</div>
                  <div v-if="personaStore.councilProgress.arguments.exiles" class="text-body-2">
                    <v-chip size="small" variant="outlined" color="orange-lighten-2" class="mr-1">感知精灵</v-chip>
                    {{ personaStore.councilProgress.arguments.exiles }}
                  </div>
                  <div v-if="personaStore.councilProgress.arguments.firefighters" class="text-body-2 mt-1">
                    <v-chip size="small" variant="outlined" color="light-green" class="mr-1">规则守卫</v-chip>
                    {{ personaStore.councilProgress.arguments.firefighters }}
                  </div>
                </div>
              </div>
            </div>
            <div v-else>
              <div class="text-subtitle-1 font-weight-bold">会议未进行</div>
              <div class="text-body-2 text-medium-emphasis">
                {{ councilHistory.length > 0 ? '会议将在情绪强度超过阈值时自动触发' : '暂无会议记录' }}
              </div>
            </div>
          </div>
          <div class="text-right">
            <div class="text-caption text-medium-emphasis">情绪强度</div>
            <div class="text-h5">{{ Math.round(personaStore.emotionIntensity * 100) }}%</div>
            <v-progress-linear
              :model-value="personaStore.emotionIntensity * 100"
              :color="emotionBarColor"
              height="8"
              rounded
              class="mt-1"
            ></v-progress-linear>
          </div>
        </div>
      </v-card-text>
    </v-card>

    <!-- 辩论日志 -->
    <v-card class="mb-6" variant="outlined">
      <v-card-title>
        <v-icon class="mr-2">mdi-timeline-text</v-icon>
        辩论日志
      </v-card-title>
      <v-card-text class="pa-0">
        <CouncilDebateLog />
      </v-card-text>
    </v-card>

    <!-- 议会历史 -->
    <v-card variant="outlined">
      <v-card-title class="d-flex align-center">
        <v-icon class="mr-2">mdi-history</v-icon>
        会议历史
        <v-spacer></v-spacer>
        <v-btn
          size="small"
          variant="text"
          @click="loadCouncilHistory"
          :loading="loadingHistory"
          :disabled="!authStore.currentSessionId"
        >
          <v-icon>mdi-refresh</v-icon>
        </v-btn>
      </v-card-title>
      <v-card-text>
        <div v-if="!authStore.currentSessionId" class="text-center pa-6">
          <v-icon size="48" class="mb-4" color="grey">mdi-account-question</v-icon>
          <p>请先开始对话以查看会议历史</p>
          <v-btn color="primary" @click="$router.push('/')" class="mt-2">前往对话</v-btn>
        </div>
        <div v-else-if="loadingHistory" class="text-center pa-6">
          <v-progress-circular indeterminate color="primary"></v-progress-circular>
        </div>
        <div v-else-if="councilHistory.length === 0" class="text-center pa-6 text-medium-emphasis">
          <v-icon size="48" class="mb-4">mdi-account-group-outline</v-icon>
          <p>暂无会议历史记录</p>
        </div>
        <v-list v-else lines="two">
          <v-list-item
            v-for="council in councilHistory"
            :key="council.council_id"
            :title="`会议 ${council.council_id.substring(0, 8)}...`"
            :subtitle="`${council.total_rounds} 轮对话 · ${formatDate(council.created_at)}`"
          >
            <template v-slot:prepend>
              <v-avatar :color="council.status === 'completed' ? 'success' : council.status === 'cancelled' ? 'error' : 'info'" size="40">
                <v-icon color="white">
                  {{ council.status === 'completed' ? 'mdi-check-circle' : council.status === 'cancelled' ? 'mdi-close-circle' : 'mdi-progress-clock' }}
                </v-icon>
              </v-avatar>
            </template>
            <template v-slot:append>
              <v-chip size="small" :color="getCouncilStatusColor(council.status)" variant="flat">
                {{ getCouncilStatusText(council.status) }}
              </v-chip>
            </template>
          </v-list-item>
        </v-list>
        <div v-if="councilHistory.length > 0" class="text-center mt-4">
          <v-btn variant="text" size="small" @click="loadMoreHistory" :disabled="!hasMoreHistory">
            加载更多
          </v-btn>
        </div>
      </v-card-text>
    </v-card>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { usePersonaStore } from '@/stores/persona'
import { useAuthStore } from '@/stores/auth'
import CouncilDebateLog from '@/components/CouncilDebateLog.vue'
import { councilApi } from '@/api/council'

const personaStore = usePersonaStore()
const authStore = useAuthStore()

// 响应式数据
const councilHistory = ref([])
const loadingHistory = ref(false)
const historyOffset = ref(0)
const historyLimit = 10
const hasMoreHistory = ref(true)

import { getEmotionColor } from '@/composables/usePersona'

// 计算属性
const emotionBarColor = computed(() => getEmotionColor(personaStore.emotionIntensity))

// 方法
const formatDate = (dateString) => {
  const date = new Date(dateString)
  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

const getCouncilStatusColor = (status) => {
  const colors = {
    'completed': 'success',
    'active': 'info',
    'paused': 'warning',
    'cancelled': 'error'
  }
  return colors[status] || 'grey'
}

const getCouncilStatusText = (status) => {
  const texts = {
    'completed': '已完成',
    'active': '进行中',
    'paused': '已暂停',
    'cancelled': '已取消'
  }
  return texts[status] || status
}

const loadCouncilHistory = async () => {
  if (!authStore.currentSessionId) return

  loadingHistory.value = true
  historyOffset.value = 0
  try {
    const response = await councilApi.getHistory(
      authStore.currentSessionId,
      historyLimit,
      0
    )
    councilHistory.value = response.data.history || []
    hasMoreHistory.value = (response.data.history?.length || 0) >= historyLimit
  } catch (error) {
    console.error('加载议会历史失败:', error)
    councilHistory.value = []
  } finally {
    loadingHistory.value = false
  }
}

const loadMoreHistory = async () => {
  if (!authStore.currentSessionId || !hasMoreHistory.value) return

  loadingHistory.value = true
  const nextOffset = historyOffset.value + historyLimit
  try {
    const response = await councilApi.getHistory(
      authStore.currentSessionId,
      historyLimit,
      nextOffset
    )
    const newHistory = response.data.history || []
    councilHistory.value = [...councilHistory.value, ...newHistory]
    hasMoreHistory.value = newHistory.length >= historyLimit
    historyOffset.value = nextOffset
  } catch (error) {
    console.error('加载更多议会历史失败:', error)
  } finally {
    loadingHistory.value = false
  }
}

// 生命周期
onMounted(() => {
  if (authStore.currentSessionId) {
    loadCouncilHistory()
  }
})
</script>

<style scoped>
/* 议会状态卡片中的进度条 */
.v-progress-linear {
  border-radius: 4px;
}

/* 议会历史列表项悬停效果 */
.v-list-item:hover {
  background-color: rgba(0, 0, 0, 0.02);
}

/* 标题图标颜色 */
.v-icon.mdi-account-group {
  color: var(--v-primary-base);
}
</style>
