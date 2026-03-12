<template>
  <v-container class="pa-4">
    <!-- 返回按钮 -->
    <v-btn color="secondary" class="mb-6" @click="$router.push('/history')">
      <v-icon left>mdi-arrow-left</v-icon>返回历史版本
    </v-btn>

    <!-- 加载状态 -->
    <v-progress-linear
      v-if="loading"
      indeterminate
      color="primary"
      class="mb-4"
    ></v-progress-linear>

    <!-- 详情卡片 -->
    <v-card v-if="snapshot" class="mb-6">
      <v-card-title class="d-flex align-center">
        <v-avatar :color="getPersonaColor(snapshot.persona)" size="56" class="mr-3">
          <v-icon dark size="28">{{ getPersonaIcon(snapshot.persona) }}</v-icon>
        </v-avatar>
        <div>
          <div class="text-h5 font-weight-bold">{{ formatPersona(snapshot.persona) }}</div>
          <div class="text-body-2 text-disabled">版本ID: {{ snapshot.id }}</div>
        </div>
        <v-spacer></v-spacer>
        <div class="text-right">
          <v-chip class="mr-2" :color="getIntensityColor(snapshot.emotion_intensity)" size="large">
            <v-icon start>mdi-emoticon-outline</v-icon>
            {{ (snapshot.emotion_intensity * 100).toFixed(0) }}% 情绪强度
          </v-chip>
          <v-chip color="blue-grey" size="large">
            <v-icon start>mdi-message-text</v-icon>
            {{ snapshot.message_count }} 条消息
          </v-chip>
        </div>
      </v-card-title>

      <v-card-text>
        <!-- 基本信息 -->
        <v-row class="mb-6">
          <v-col cols="12" md="6">
            <v-list density="compact">
              <v-list-subheader>基本信息</v-list-subheader>
              <v-list-item>
                <template v-slot:prepend>
                  <v-icon>mdi-identifier</v-icon>
                </template>
                <v-list-item-title>版本哈希</v-list-item-title>
                <v-list-item-subtitle>{{ snapshot.id }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item>
                <template v-slot:prepend>
                  <v-icon>mdi-account</v-icon>
                </template>
                <v-list-item-title>伙伴状态</v-list-item-title>
                <v-list-item-subtitle>{{ formatPersona(snapshot.persona) }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item>
                <template v-slot:prepend>
                  <v-icon>mdi-calendar</v-icon>
                </template>
                <v-list-item-title>创建时间</v-list-item-title>
                <v-list-item-subtitle>{{ formatDate(snapshot.created_at) }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item>
                <template v-slot:prepend>
                  <v-icon>mdi-folder</v-icon>
                </template>
                <v-list-item-title>会话ID</v-list-item-title>
                <v-list-item-subtitle>{{ snapshot.session_id }}</v-list-item-subtitle>
              </v-list-item>
            </v-list>
          </v-col>
          <v-col cols="12" md="6">
            <v-list density="compact">
              <v-list-subheader>标签</v-list-subheader>
              <v-list-item v-if="snapshot.tags && snapshot.tags.length > 0">
                <div class="d-flex flex-wrap">
                  <v-chip
                    v-for="tag in snapshot.tags"
                    :key="tag"
                    color="secondary"
                    class="mr-2 mb-2"
                  >
                    {{ tag }}
                  </v-chip>
                </div>
              </v-list-item>
              <v-list-item v-else>
                <v-list-item-title>无标签</v-list-item-title>
              </v-list-item>
            </v-list>
          </v-col>
        </v-row>

        <!-- 状态数据 -->
        <v-expansion-panels class="mb-6">
          <v-expansion-panel>
            <v-expansion-panel-title>
              <v-icon left>mdi-code-json</v-icon>
              <span class="font-weight-bold">状态数据</span>
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <pre class="state-data">{{ JSON.stringify(snapshot.metadata, null, 2) }}</pre>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>

        <!-- 操作按钮 -->
        <v-card-actions class="px-0">
          <v-btn
            color="primary"
            size="large"
            @click="restoreSnapshot"
            :loading="restoring"
          >
            <v-icon left>mdi-restore</v-icon>
            恢复到此版本
          </v-btn>
          <v-btn
            color="error"
            size="large"
            variant="outlined"
            @click="deleteSnapshot"
            :loading="deleting"
          >
            <v-icon left>mdi-delete</v-icon>
            删除此版本
          </v-btn>
          <v-spacer></v-spacer>
          <v-btn
            color="grey"
            variant="text"
            @click="copySnapshotId"
          >
            <v-icon left>mdi-content-copy</v-icon>
            复制ID
          </v-btn>
        </v-card-actions>
      </v-card-text>
    </v-card>

    <!-- 未找到 -->
    <v-card v-else-if="!loading">
      <v-card-text class="text-center py-12">
        <v-icon size="64" color="grey-lighten-1" class="mb-4">mdi-magnify</v-icon>
        <h3 class="text-h5 mb-2">版本未找到</h3>
        <p class="text-body-1 text-disabled mb-4">请求的版本不存在或已被删除</p>
        <v-btn color="primary" @click="$router.push('/history')">返回历史版本</v-btn>
      </v-card-text>
    </v-card>
  </v-container>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { versionApi } from '@/api/version'

const route = useRoute()
const router = useRouter()

// 状态
const snapshot = ref(null)
const loading = ref(false)
const restoring = ref(false)
const deleting = ref(false)

// 获取快照ID
const snapshotId = computed(() => route.params.id)

// 加载快照详情
const loadSnapshot = async () => {
  if (!snapshotId.value) return

  loading.value = true
  try {
    const response = await versionApi.getSnapshot(snapshotId.value)
    snapshot.value = response.data
  } catch (error) {
    console.error('加载快照详情失败:', error)
    window.$snackbar('加载版本详情失败', 'error')
    snapshot.value = null
  } finally {
    loading.value = false
  }
}

// 恢复快照
const restoreSnapshot = async () => {
  if (!snapshot.value) return
  if (!confirm('确定要恢复到此版本吗？当前状态将被覆盖。')) {
    return
  }

  restoring.value = true
  try {
    await versionApi.restoreSnapshot(snapshot.value.session_id, snapshot.value.id)
    window.$snackbar('版本恢复成功', 'success')
    // 可以重定向到对话页面或其他操作
    router.push('/')
  } catch (error) {
    console.error('恢复快照失败:', error)
    window.$snackbar('恢复版本失败', 'error')
  } finally {
    restoring.value = false
  }
}

// 删除快照
const deleteSnapshot = async () => {
  if (!snapshot.value) return
  if (!confirm('确定要删除此版本吗？此操作不可撤销。')) {
    return
  }

  deleting.value = true
  try {
    await versionApi.deleteSnapshot(snapshot.value.id)
    window.$snackbar('版本删除成功', 'success')
    router.push('/history')
  } catch (error) {
    console.error('删除快照失败:', error)
    window.$snackbar('删除版本失败', 'error')
  } finally {
    deleting.value = false
  }
}

// 复制快照ID
const copySnapshotId = () => {
  if (!snapshot.value) return
  navigator.clipboard.writeText(snapshot.value.id)
    .then(() => window.$snackbar('已复制版本ID', 'success'))
    .catch(() => window.$snackbar('复制失败', 'error'))
}

// 工具函数
const formatDate = (dateString) => {
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

const formatPersona = (persona) => {
  const map = {
    manager: '安全岛',
    exiles: '感知精灵',
    firefighters: '规则守卫',
    healer: '星星向导'
  }
  return map[persona] || persona
}

const getPersonaColor = (persona) => {
  const colors = {
    manager: 'blue',
    exiles: 'orange',
    firefighters: 'green',
    healer: 'purple'
  }
  return colors[persona] || 'grey'
}

const getPersonaIcon = (persona) => {
  const icons = {
    manager: 'mdi-island',
    exiles: 'mdi-creation',
    firefighters: 'mdi-shield-star',
    healer: 'mdi-star-shooting'
  }
  return icons[persona] || 'mdi-account'
}

const getIntensityColor = (intensity) => {
  if (intensity < 0.3) return 'green'
  if (intensity < 0.7) return 'orange'
  return 'red'
}

// 生命周期
onMounted(() => {
  loadSnapshot()
})
</script>

<style scoped>
.state-data {
  background-color: #f5f5f5;
  border-radius: 4px;
  padding: 16px;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 12px;
  line-height: 1.5;
  max-height: 400px;
  overflow: auto;
}
</style>