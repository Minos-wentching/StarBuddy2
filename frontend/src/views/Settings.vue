<template>
  <div class="settings-root">
    <ShaderBackground role="manager" :intensity="0.15" />

    <div class="settings-scroll">
      <!-- Header -->
      <div class="settings-header">
        <v-btn icon variant="text" size="small" @click="$router.push('/')" class="back-btn">
          <v-icon>mdi-arrow-left</v-icon>
        </v-btn>
        <h1 class="settings-title">设置</h1>
        <p class="settings-subtitle">个性化配置和账户管理</p>
      </div>

      <!-- 用户信息 -->
      <div class="glass-card mb-4">
        <div class="card-header">
          <v-icon size="20" color="white" class="mr-2">mdi-account</v-icon>
          <span class="card-title">用户信息</span>
        </div>
        <div v-if="authStore.user" class="card-body">
          <v-form @submit.prevent="updateUserProfile">
            <div class="field-row">
              <v-text-field
                v-model="userForm.username"
                label="用户名"
                variant="outlined"
                density="compact"
                color="white"
                base-color="rgba(255,255,255,0.4)"
                :loading="loading"
                :disabled="loading"
                :rules="[v => !!v || '用户名不能为空', v => v.length >= 3 || '用户名至少3个字符']"
                class="mb-3"
              />
              <v-text-field
                v-model="userForm.email"
                label="邮箱"
                variant="outlined"
                density="compact"
                color="white"
                base-color="rgba(255,255,255,0.4)"
                type="email"
                :disabled="true"
                hint="邮箱功能开发中"
                persistent-hint
                class="mb-3"
              />
            </div>
            <div class="btn-row">
              <v-btn variant="tonal" color="white" size="small" class="text-none" type="submit" :loading="loading" :disabled="!isFormChanged">
                保存更改
              </v-btn>
              <v-btn variant="text" size="small" class="text-none ml-2" style="color:rgba(255,255,255,0.5)" @click="resetForm" :disabled="!isFormChanged || loading">
                重置
              </v-btn>
            </div>
          </v-form>
        </div>
        <div v-else class="card-body text-center" style="padding:24px 0">
          <v-icon size="40" style="color:rgba(255,255,255,0.25)">mdi-account-question</v-icon>
          <p style="color:rgba(255,255,255,0.5);margin-top:8px">未登录用户</p>
          <v-btn variant="tonal" color="white" size="small" class="text-none mt-2" @click="$router.push('/login')">前往登录</v-btn>
        </div>
      </div>

      <!-- 应用设置 -->
      <div class="glass-card mb-4">
        <div class="card-header">
          <v-icon size="20" color="white" class="mr-2">mdi-application-cog</v-icon>
          <span class="card-title">应用设置</span>
        </div>
        <div class="card-body">
          <div class="settings-grid">
            <div class="settings-col">
              <div class="section-label">主题设置</div>
              <v-select
                v-model="appSettings.theme"
                :items="themeOptions"
                label="主题模式"
                variant="outlined"
                density="compact"
                color="white"
                base-color="rgba(255,255,255,0.4)"
                hide-details
                @update:model-value="saveAppSettings"
                class="mb-3"
              />
              <v-switch
                v-model="appSettings.reduceAnimations"
                label="减少动画效果"
                hide-details
                color="white"
                density="compact"
                @update:model-value="saveAppSettings"
              />
              <v-switch
                v-model="appSettings.minimalMode"
                label="极简模式"
                hide-details
                color="white"
                density="compact"
                @update:model-value="saveAppSettings"
              />
            </div>
            <div class="settings-col">
              <div class="section-label">通知设置</div>
              <v-switch
                v-model="appSettings.notifications.enabled"
                label="启用通知"
                hide-details
                color="white"
                density="compact"
                @update:model-value="saveAppSettings"
              />
              <div v-if="appSettings.notifications.enabled">
                <v-switch
                  v-model="appSettings.notifications.sound"
                  label="提示音"
                  hide-details
                  color="white"
                  density="compact"
                  @update:model-value="saveAppSettings"
                />
                <v-switch
                  v-model="appSettings.notifications.councilUpdates"
                  label="会议更新通知"
                  hide-details
                  color="white"
                  density="compact"
                  @update:model-value="saveAppSettings"
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 数据管理 -->
      <div class="glass-card mb-4">
        <div class="card-header">
          <v-icon size="20" color="white" class="mr-2">mdi-database</v-icon>
          <span class="card-title">数据管理</span>
        </div>
        <div class="card-body">
          <div class="settings-grid">
            <div class="settings-col">
              <div class="section-label">本地数据</div>
              <v-btn variant="outlined" size="small" class="text-none mb-2 glass-btn" @click="confirmClearLocalData" :loading="clearingData">
                <v-icon start size="16">mdi-delete</v-icon>
                清除本地缓存
              </v-btn>
              <p class="hint-text">清除本地存储的会话数据和临时文件</p>
              <v-btn variant="outlined" size="small" class="text-none mt-3 glass-btn" @click="exportUserData" :disabled="!authStore.user">
                <v-icon start size="16">mdi-download</v-icon>
                导出个人数据
              </v-btn>
              <p class="hint-text">导出会话历史、会议记录和行为模式数据</p>
            </div>
            <div class="settings-col">
              <div class="section-label">会话管理</div>
              <v-btn variant="outlined" size="small" class="text-none mb-2 glass-btn" @click="createSessionSnapshot" :loading="creatingSnapshot" :disabled="!authStore.currentSessionId">
                <v-icon start size="16">mdi-content-save</v-icon>
                创建会话快照
              </v-btn>
              <p class="hint-text">保存当前会话状态，便于后续恢复</p>
              <v-btn variant="outlined" size="small" class="text-none mt-3 glass-btn" @click="$router.push('/history')">
                <v-icon start size="16">mdi-history</v-icon>
                查看历史记录
              </v-btn>
              <p class="hint-text">查看和管理所有历史会话</p>
            </div>
          </div>
        </div>
      </div>

      <!-- 账户操作 -->
      <div class="glass-card mb-4">
        <div class="card-header">
          <v-icon size="20" color="white" class="mr-2">mdi-shield-account</v-icon>
          <span class="card-title">账户操作</span>
        </div>
        <div class="card-body">
          <div class="settings-grid">
            <div class="settings-col">
              <div class="section-label">安全设置</div>
              <v-btn variant="outlined" size="small" class="text-none mb-2 glass-btn" :disabled="true">
                <v-icon start size="16">mdi-lock-reset</v-icon>
                修改密码
              </v-btn>
              <p class="hint-text">密码修改功能开发中</p>
              <v-btn variant="outlined" size="small" class="text-none mt-3 glass-btn" @click="showTokenInfo">
                <v-icon start size="16">mdi-key</v-icon>
                查看令牌信息
              </v-btn>
              <p class="hint-text">查看当前认证令牌状态</p>
            </div>
            <div class="settings-col">
              <div class="section-label">账户操作</div>
              <v-btn variant="outlined" size="small" class="text-none mb-2 glass-btn danger-btn" @click="confirmLogout">
                <v-icon start size="16">mdi-logout</v-icon>
                退出登录
              </v-btn>
              <p class="hint-text">安全退出当前账户</p>
              <v-btn variant="outlined" size="small" class="text-none mt-3 glass-btn danger-btn" :disabled="true">
                <v-icon start size="16">mdi-account-remove</v-icon>
                删除账户
              </v-btn>
              <p class="hint-text">永久删除账户及相关数据（功能开发中）</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 确认对话框 -->
    <v-dialog v-model="showConfirmDialog" max-width="400">
      <div class="glass-card dialog-card">
        <div class="card-header"><span class="card-title">确认操作</span></div>
        <div class="card-body">{{ confirmMessage }}</div>
        <div class="btn-row" style="justify-content:flex-end;padding-top:12px">
          <v-btn variant="text" size="small" class="text-none" style="color:rgba(255,255,255,0.5)" @click="showConfirmDialog = false">取消</v-btn>
          <v-btn variant="tonal" color="white" size="small" class="text-none ml-2" @click="executeConfirmedAction">确认</v-btn>
        </div>
      </div>
    </v-dialog>

    <!-- 令牌信息对话框 -->
    <v-dialog v-model="showTokenDialog" max-width="500">
      <div class="glass-card dialog-card">
        <div class="card-header">
          <v-icon size="18" color="white" class="mr-2">mdi-key</v-icon>
          <span class="card-title">令牌信息</span>
        </div>
        <div class="card-body" v-if="authStore.token">
          <div class="token-row"><span class="token-label">访问令牌:</span><span class="token-value">{{ maskToken(authStore.token) }}</span></div>
          <div class="token-row"><span class="token-label">刷新令牌:</span><span class="token-value">{{ authStore.refreshToken ? maskToken(authStore.refreshToken) : '无' }}</span></div>
          <div class="token-row"><span class="token-label">用户ID:</span><span class="token-value">{{ authStore.userId }}</span></div>
          <div class="token-row"><span class="token-label">令牌状态:</span><span class="token-status">有效</span></div>
        </div>
        <div class="card-body text-center" v-else style="padding:24px 0">
          <v-icon size="40" style="color:rgba(255,255,255,0.25)">mdi-key-remove</v-icon>
          <p style="color:rgba(255,255,255,0.5);margin-top:8px">无有效令牌</p>
        </div>
        <div class="btn-row" style="justify-content:flex-end;padding-top:12px">
          <v-btn variant="tonal" color="white" size="small" class="text-none" @click="showTokenDialog = false">关闭</v-btn>
        </div>
      </div>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import ShaderBackground from '@/components/ShaderBackground.vue'

const authStore = useAuthStore()

const userForm = reactive({ username: '', email: '' })
const loading = ref(false)
const clearingData = ref(false)
const creatingSnapshot = ref(false)

const appSettings = reactive({
  theme: 'auto',
  reduceAnimations: false,
  minimalMode: false,
  notifications: { enabled: true, sound: true, councilUpdates: true }
})

const themeOptions = [
  { title: '自动', value: 'auto' },
  { title: '浅色', value: 'light' },
  { title: '深色', value: 'dark' }
]

const showConfirmDialog = ref(false)
const showTokenDialog = ref(false)
const confirmMessage = ref('')
const confirmedAction = ref(null)

const isFormChanged = computed(() => {
  if (!authStore.user) return false
  return userForm.username !== authStore.user.username
})

const resetForm = () => {
  if (authStore.user) {
    userForm.username = authStore.user.username || ''
    userForm.email = authStore.user.email || ''
  }
}

const updateUserProfile = async () => {
  if (!authStore.user) return
  loading.value = true
  try {
    const result = await authStore.updateProfile({ username: userForm.username })
    if (!result.success) console.error('更新失败:', result.error)
  } catch (error) {
    console.error('更新用户信息失败:', error)
  } finally {
    loading.value = false
  }
}

const saveAppSettings = () => {
  localStorage.setItem('appSettings', JSON.stringify(appSettings))
  window.dispatchEvent(new CustomEvent('appSettingsChanged', { detail: appSettings }))
}

const loadAppSettings = () => {
  const saved = localStorage.getItem('appSettings')
  if (saved) {
    try { Object.assign(appSettings, JSON.parse(saved)) } catch {}
  }
}

const confirmClearLocalData = () => {
  confirmMessage.value = '确定要清除本地缓存吗？这将删除所有本地存储的会话数据和临时文件。'
  confirmedAction.value = 'clearLocalData'
  showConfirmDialog.value = true
}

const clearLocalData = () => {
  clearingData.value = true
  try {
    const keepItems = ['access_token', 'refresh_token', 'user', 'appSettings']
    Object.keys(localStorage).forEach(key => {
      if (!keepItems.includes(key)) localStorage.removeItem(key)
    })
  } finally {
    clearingData.value = false
  }
}

const exportUserData = () => {
  const exportData = { user: authStore.user, timestamp: new Date().toISOString(), exportType: 'user_data' }
  const dataBlob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(dataBlob)
  const link = document.createElement('a')
  link.href = url
  link.download = `starbuddy-export-${new Date().toISOString().slice(0, 10)}.json`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

const createSessionSnapshot = () => {
  creatingSnapshot.value = true
  setTimeout(() => { creatingSnapshot.value = false }, 1000)
}

const maskToken = (token) => {
  if (!token || token.length < 12) return '******'
  return token.substring(0, 6) + '••••••••' + token.substring(token.length - 6)
}

const showTokenInfo = () => { showTokenDialog.value = true }

const confirmLogout = () => {
  confirmMessage.value = '确定要退出登录吗？'
  confirmedAction.value = 'logout'
  showConfirmDialog.value = true
}

const executeConfirmedAction = () => {
  showConfirmDialog.value = false
  if (confirmedAction.value === 'clearLocalData') clearLocalData()
  else if (confirmedAction.value === 'logout') authStore.logout()
  confirmedAction.value = null
}

onMounted(() => {
  resetForm()
  loadAppSettings()
})
</script>

<style scoped>
.settings-root {
  position: fixed;
  inset: 0;
  overflow: hidden;
}
.settings-scroll {
  position: relative;
  z-index: 10;
  height: 100vh;
  overflow-y: auto;
  padding: 24px 20px 60px;
  max-width: 600px;
  margin: 0 auto;
}
.settings-header {
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
.settings-title {
  font-size: 26px;
  font-weight: 700;
  color: white;
  letter-spacing: 2px;
}
.settings-subtitle {
  font-size: 13px;
  color: rgba(255,255,255,0.5);
  margin-top: 4px;
}
.glass-card {
  background: rgba(255,255,255,0.06);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 12px;
  padding: 16px;
}
.card-header {
  display: flex;
  align-items: center;
  margin-bottom: 14px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(255,255,255,0.08);
}
.card-title {
  font-size: 15px;
  font-weight: 600;
  color: rgba(255,255,255,0.85);
}
.card-body {
  color: rgba(255,255,255,0.7);
  font-size: 13px;
}
.section-label {
  font-size: 13px;
  font-weight: 600;
  color: rgba(255,255,255,0.7);
  margin-bottom: 10px;
}
.settings-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}
@media (max-width: 600px) {
  .settings-grid {
    grid-template-columns: 1fr;
  }
}
.field-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
@media (max-width: 600px) {
  .field-row {
    grid-template-columns: 1fr;
  }
}
.btn-row {
  display: flex;
  align-items: center;
}
.hint-text {
  font-size: 11px;
  color: rgba(255,255,255,0.35);
  margin-top: 4px;
}
.mode-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.mode-actions {
  margin-top: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.dark-chip {
  background: rgba(255,255,255,0.14) !important;
  color: rgba(255,255,255,0.86) !important;
  border: 1px solid rgba(255,255,255,0.22);
}
.glass-btn {
  color: rgba(255,255,255,0.7) !important;
  border-color: rgba(255,255,255,0.2) !important;
}
.glass-btn:hover {
  background: rgba(255,255,255,0.08) !important;
}
.danger-btn {
  color: #ef5350 !important;
  border-color: rgba(239,83,80,0.3) !important;
}
.danger-btn:hover {
  background: rgba(239,83,80,0.1) !important;
}
.dialog-card {
  background: rgba(30,30,40,0.92);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
}
.token-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
.token-label {
  font-size: 12px;
  font-weight: 600;
  color: rgba(255,255,255,0.6);
  min-width: 70px;
}
.token-value {
  font-size: 11px;
  color: rgba(255,255,255,0.5);
  font-family: monospace;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.token-status {
  font-size: 11px;
  color: #66bb6a;
  font-weight: 600;
}

/* Vuetify dark overrides */
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
:deep(.v-switch .v-label) {
  color: rgba(255,255,255,0.6) !important;
  font-size: 13px;
}
:deep(.v-switch .v-selection-control__wrapper) {
  color: rgba(255,255,255,0.3);
}
:deep(.v-messages__message) {
  color: rgba(255,255,255,0.35) !important;
}
</style>
