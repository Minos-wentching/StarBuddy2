<template>
  <div class="healing-album pa-4">
    <div v-if="!images.length" class="d-flex flex-column align-center justify-center" style="min-height: 200px">
      <v-icon size="48" color="rgba(255,255,255,0.3)">mdi-image-multiple</v-icon>
      <p class="mt-2" style="color: rgba(255,255,255,0.5); font-size: 14px">暂无感知图片</p>
      <p style="color: rgba(255,255,255,0.3); font-size: 12px">当伙伴活跃时，系统会自动生成意象图片</p>
    </div>

    <div v-else class="album-grid">
      <div v-for="img in images" :key="img.id" class="album-item" @click="openDetail(img)">
        <div class="album-img-wrap">
          <v-img :src="buildImageSrc(img.image_url)" height="160" cover class="album-img">
            <template v-slot:placeholder>
              <div class="d-flex align-center justify-center fill-height">
                <v-progress-circular indeterminate color="rgba(255,255,255,0.5)" size="24"></v-progress-circular>
              </div>
            </template>
            <template v-slot:error>
              <div class="d-flex align-center justify-center fill-height" style="background: rgba(255,255,255,0.05)">
                <v-icon size="32" color="rgba(255,255,255,0.3)">mdi-image-broken</v-icon>
              </div>
            </template>
          </v-img>
        </div>
        <div class="album-info">
          <div class="album-text">{{ img.diary_text }}</div>
          <div class="d-flex align-center mt-1">
            <span class="album-persona" :style="{ color: getPersonaColor(img.persona) }">
              {{ getPersonaName(img.persona) }}
            </span>
            <span class="album-date">{{ formatDate(img.created_at) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Detail dialog -->
    <v-dialog v-model="detailOpen" max-width="600">
      <div v-if="selectedImage" class="detail-card">
        <v-img :src="buildImageSrc(selectedImage.image_url)" max-height="400" contain class="detail-img"></v-img>
        <div class="detail-body">
          <p class="detail-text">{{ selectedImage.diary_text }}</p>
          <div class="feedback-box mt-4">
            <div class="feedback-title">写下你此刻的感受</div>
            <v-textarea
              v-model="feedbackText"
              variant="outlined"
              density="comfortable"
              auto-grow
              rows="2"
              max-rows="4"
              :disabled="feedbackLoading || !selectedImage?.id"
              placeholder="例如：这段日记让我有点难过，也有些被理解的感觉..."
              hide-details
            />
            <div v-if="selectedImage.feedback" class="feedback-history mt-2">
              已记录反馈：{{ selectedImage.feedback }}
            </div>
            <div class="d-flex justify-end mt-2">
              <v-btn
                color="primary"
                size="small"
                :loading="feedbackLoading"
                :disabled="!feedbackText.trim() || feedbackLoading"
                @click="submitFeedback"
              >
                提交反馈
              </v-btn>
            </div>
          </div>
          <div class="d-flex align-center justify-space-between mt-3">
            <span class="album-persona" :style="{ color: getPersonaColor(selectedImage.persona) }">
              {{ getPersonaName(selectedImage.persona) }}
            </span>
            <v-btn variant="text" size="small" @click="detailOpen = false" style="color: rgba(255,255,255,0.6)">
              关闭
            </v-btn>
          </div>
        </div>
      </div>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { usePersonaStore } from '@/stores/persona'
import { useDialogueStore } from '@/stores/dialogue'
import { imageApi } from '@/api/image'

const authStore = useAuthStore()
const personaStore = usePersonaStore()
const dialogueStore = useDialogueStore()
const images = ref([])
const detailOpen = ref(false)
const selectedImage = ref(null)
const feedbackText = ref('')
const feedbackLoading = ref(false)

const getPersonaName = (p) => ({ manager: '安全岛', exiles: '感知精灵', firefighters: '规则守卫', counselor: '星星向导' }[p] || p)
const getPersonaColor = (p) => ({
  exiles: '#F4B183', firefighters: '#A9D18E', manager: '#5B9BD5', counselor: '#B4A7D6'
}[p] || 'rgba(255,255,255,0.6)')
const formatDate = (d) => d ? new Date(d).toLocaleDateString() : ''
const buildImageSrc = (url) => {
  const raw = String(url || '').trim()
  if (!raw) return ''

  const token = String(authStore.token || '').replace(/^Bearer\s+/i, '')
  if (!token) return raw

  // 仅对受保护的本地图片接口追加 token，外链图片保持原样
  if (!raw.startsWith('/api/')) {
    return raw
  }

  const hasQuery = raw.includes('?')
  const separator = hasQuery ? '&' : '?'
  return `${raw}${separator}token=${encodeURIComponent(token)}`
}

const openDetail = (img) => {
  selectedImage.value = img
  feedbackText.value = ''
  detailOpen.value = true
}

const loadImages = async () => {
  if (!authStore.currentSessionId) return
  try {
    const res = await imageApi.getImages(authStore.currentSessionId)
    images.value = res.data.images || []
    if (selectedImage.value?.id) {
      const latest = images.value.find(i => i.id === selectedImage.value.id)
      if (latest) selectedImage.value = latest
    }
  } catch (e) {
    console.warn('加载相册失败:', e)
  }
}

const submitFeedback = async () => {
  if (!selectedImage.value?.id || !feedbackText.value.trim()) return
  feedbackLoading.value = true
  try {
    const res = await imageApi.addFeedback({
      diary_id: selectedImage.value.id,
      feedback: feedbackText.value.trim(),
    })
    const payload = res.data || {}
    if (payload.active_agent) {
      personaStore.switchPersona(payload.active_agent, Number(payload.intensity || 0), '日记反馈')
    }
    dialogueStore.addSystemMessage(payload.message || '反馈已提交')
    feedbackText.value = ''
    await loadImages()
  } catch (e) {
    console.warn('提交反馈失败:', e)
    dialogueStore.addSystemMessage('反馈提交失败，请稍后重试。')
  } finally {
    feedbackLoading.value = false
  }
}

const handleDiaryUpdate = () => {
  loadImages()
}

onMounted(async () => {
  await loadImages()
  window.addEventListener('starbuddy:diary-update', handleDiaryUpdate)
})

onBeforeUnmount(() => {
  window.removeEventListener('starbuddy:diary-update', handleDiaryUpdate)
})
</script>

<style scoped>
.album-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.album-item {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.2s ease;
}
.album-item:hover {
  background: rgba(255, 255, 255, 0.1);
  transform: translateY(-2px);
}

.album-img-wrap {
  overflow: hidden;
}

.album-info {
  padding: 10px 12px;
}

.album-text {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.8);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.album-persona {
  font-size: 11px;
  font-weight: 600;
}

.album-date {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.35);
  margin-left: auto;
}

/* Detail dialog */
.detail-card {
  background: rgba(30, 30, 50, 0.95);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  overflow: hidden;
}

.detail-body {
  padding: 16px 20px;
}

.detail-text {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.85);
  line-height: 1.6;
}

.feedback-box {
  border-top: 1px solid rgba(255, 255, 255, 0.12);
  padding-top: 12px;
}

.feedback-title {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.8);
  margin-bottom: 8px;
}

.feedback-history {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
  white-space: pre-wrap;
}
</style>
