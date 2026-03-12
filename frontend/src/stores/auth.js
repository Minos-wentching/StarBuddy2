/**
 * 认证状态管理
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/auth'
import { dialogueApi } from '@/api/dialogue'
import { useRouter } from 'vue-router'
import { useDialogueStore } from '@/stores/dialogue'
import { usePersonaStore } from '@/stores/persona'
import { useShowcaseStore } from '@/stores/showcase'

export const useAuthStore = defineStore('auth', () => {
  const router = useRouter()
  const dialogueStore = useDialogueStore()
  const personaStore = usePersonaStore()
  const showcaseStore = useShowcaseStore()

  // 状态
  const user = ref(null)
  const token = ref(localStorage.getItem('access_token') || '')
  const refreshToken = ref(localStorage.getItem('refresh_token') || '')
  const isLoading = ref(false)
  const error = ref(null)
  const currentSessionId = ref(localStorage.getItem('current_session_id') || '')

  // 计算属性
  const isAuthenticated = computed(() => !!token.value && !!user.value)
  const userName = computed(() => user.value?.username || '')
  const userId = computed(() => user.value?.id || null)
  const needsOnboarding = computed(() => {
    const settings = user.value?.settings || {}
    if (settings.ifs_onboarding_completed === true) return false

    // Backward compatibility: treat users with an existing onboarding payload as onboarded,
    // even if the boolean flag is missing (older accounts / partial migrations).
    const onboarding = settings.ifs_onboarding
    if (onboarding && typeof onboarding === 'object') {
      const hasBeliefs = Array.isArray(onboarding.core_beliefs) && onboarding.core_beliefs.length > 0
      const hasDigest = typeof onboarding.profile_digest === 'string' && onboarding.profile_digest.trim().length > 0
      const hasPortraits = onboarding.persona_portraits && typeof onboarding.persona_portraits === 'object'
        ? Object.keys(onboarding.persona_portraits).length > 0
        : false
      const hasOrbs = Boolean(onboarding.memory_orbs_initialized || onboarding.trauma_events_initialized)
      if (hasBeliefs || hasDigest || hasPortraits || hasOrbs) return false
    }

    return true
  })

  const clamp = (value, min = 0, max = 1) => {
    const num = Number(value)
    if (!Number.isFinite(num)) return min
    return Math.max(min, Math.min(max, num))
  }

  const normalizeFixedOrb = (rawOrb, index = 0) => {
    const title = String(rawOrb?.title || rawOrb?.belief || rawOrb?.trigger_event || '未命名记忆').trim()
    const triggerEvent = String(rawOrb?.triggerEvent || rawOrb?.trigger_event || title).trim()
    const traumaText = String(rawOrb?.traumaText || rawOrb?.trauma_text || triggerEvent).trim()
    const intensityRaw = Number(rawOrb?.intensity)
    const intensity = Number.isFinite(intensityRaw)
      ? (intensityRaw > 1 ? clamp(intensityRaw / 10) : clamp(intensityRaw))
      : 0.58
    const sourceType = String(rawOrb?.sourceType || rawOrb?.source_type || 'onboarding_fixed')
    const personaHint = String(rawOrb?.personaHint || rawOrb?.persona_hint || (intensity >= 0.72 ? 'firefighters' : 'exiles'))

    return {
      id: String(rawOrb?.id || `fixed_orb_${index + 1}`),
      title,
      trigger_event: triggerEvent,
      trauma_text: traumaText,
      intensity,
      persona_hint: personaHint,
      source_type: sourceType,
      created_at: String(rawOrb?.createdAt || rawOrb?.created_at || new Date().toISOString()),
      orb_rank: Number(rawOrb?.orbRank || rawOrb?.orb_rank || index + 1),
    }
  }

  const normalizeTraumaEvent = (rawEvent, index = 0) => {
    const normalized = normalizeFixedOrb({
      id: rawEvent?.event_id || rawEvent?.id,
      title: rawEvent?.title,
      trigger_event: rawEvent?.trigger_event,
      trauma_text: rawEvent?.trauma_event,
      intensity: rawEvent?.intensity,
      persona_hint: rawEvent?.persona_hint,
      source_type: rawEvent?.source_type,
      created_at: rawEvent?.created_at,
      orb_rank: rawEvent?.event_rank,
    }, index)
    return {
      event_id: normalized.id,
      title: normalized.title,
      trigger_event: normalized.trigger_event,
      trauma_event: normalized.trauma_text,
      intensity: normalized.intensity,
      persona_hint: normalized.persona_hint,
      source_type: normalized.source_type,
      created_at: normalized.created_at,
      updated_at: new Date().toISOString(),
      event_rank: normalized.orb_rank,
    }
  }

  const buildFixedMemoryOrbs = (answers = {}, onboardingPayload = {}, existingFixed = []) => {
    if (Array.isArray(existingFixed) && existingFixed.length > 0) {
      return existingFixed.map((orb, index) => normalizeFixedOrb(orb, index))
    }

    const coreBeliefs = Array.isArray(onboardingPayload?.core_beliefs) ? onboardingPayload.core_beliefs : []
    const fromBeliefs = coreBeliefs
      .slice(0, 8)
      .map((belief, index) => normalizeFixedOrb({
        id: String(belief?.belief_id || `belief_${index + 1}`),
        title: String(belief?.content || '核心记忆'),
        trigger_event: String(belief?.origin_event || belief?.content || '当前情绪触发'),
        trauma_text: String(belief?.origin_event || belief?.content || '一次仍在影响你的情绪触发。'),
        intensity: Number(belief?.intensity || 6),
        persona_hint: Number(belief?.valence || 0) < -0.2 ? 'firefighters' : 'exiles',
        source_type: 'onboarding_core_belief',
      }, index))

    if (fromBeliefs.length > 0) return fromBeliefs

    const q1 = String(answers?.question_1 || '').trim()
    const q2 = String(answers?.question_2 || '').trim()
    const fallback = [
      q1
        ? {
            id: 'onboarding_q1',
            title: '问题一记忆',
            trigger_event: q1.slice(0, 28),
            trauma_text: q1,
            intensity: 0.64,
            persona_hint: 'exiles',
            source_type: 'onboarding_answer',
          }
        : null,
      q2
        ? {
            id: 'onboarding_q2',
            title: '问题二记忆',
            trigger_event: q2.slice(0, 28),
            trauma_text: q2,
            intensity: 0.68,
            persona_hint: 'firefighters',
            source_type: 'onboarding_answer',
          }
        : null,
    ].filter(Boolean)

    return fallback.map((orb, index) => normalizeFixedOrb(orb, index))
  }

  // 从localStorage加载用户信息
  const savedUser = localStorage.getItem('user')
  if (savedUser) {
    try {
      user.value = JSON.parse(savedUser)
    } catch (e) {
      console.error('解析用户信息失败:', e)
      localStorage.removeItem('user')
    }
  }

  // 方法
  const setTokens = (accessToken, refreshTokenValue) => {
    token.value = accessToken
    refreshToken.value = refreshTokenValue || ''

    localStorage.setItem('access_token', accessToken)
    if (refreshTokenValue) {
      localStorage.setItem('refresh_token', refreshTokenValue)
    }
  }

  const setUser = (userData) => {
    user.value = userData
    localStorage.setItem('user', JSON.stringify(userData))
    showcaseStore.bindUser(userData?.id)
  }

  const resetRuntimeStores = () => {
    dialogueStore.clearMessages()
    dialogueStore.currentSessionId = ''
    dialogueStore.sessionStatus = {
      isActive: true,
      messageCount: 0,
      lastActivity: null
    }
    personaStore.resetState()
    showcaseStore.stopDemo()
    showcaseStore.bindUser('')
  }

  const clearAuth = () => {
    resetRuntimeStores()
    user.value = null
    token.value = ''
    refreshToken.value = ''
    currentSessionId.value = ''

    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user')
    localStorage.removeItem('current_session_id')
  }

  const setSessionId = (sessionId) => {
    currentSessionId.value = sessionId || ''
    if (sessionId) {
      localStorage.setItem('current_session_id', sessionId)
    } else {
      localStorage.removeItem('current_session_id')
    }
  }

  const createDefaultSession = async () => {
    try {
      const res = await dialogueApi.createSession({ session_name: '新会话' })
      setSessionId(res.data.id)
      return res.data.id
    } catch (err) {
      console.error('创建默认会话失败:', err)
      return ''
    }
  }

  const resumeOrCreateSession = async () => {
    try {
      const sessionsRes = await dialogueApi.listSessions()
      const sessions = sessionsRes.data?.sessions || []
      if (sessions.length > 0 && sessions[0]?.id) {
        setSessionId(sessions[0].id)
        return sessions[0].id
      }
    } catch (err) {
      console.warn('获取会话列表失败，转为新建会话:', err)
    }
    return await createDefaultSession()
  }

  // 注册
  const register = async (username) => {
    isLoading.value = true
    error.value = null

    try {
      const response = await authApi.register({ username })
      // 注册后不自动登录，返回用户数据
      return { success: true, data: response.data }
    } catch (err) {
      error.value = err.response?.data?.detail || '注册失败'
      return { success: false, error: error.value }
    } finally {
      isLoading.value = false
    }
  }

  // 登录
  const login = async (username) => {
    isLoading.value = true
    error.value = null

    try {
      clearAuth()
      const response = await authApi.login({ username })

      // 设置令牌
      setTokens(response.data.access_token, response.data.refresh_token)

      // 获取用户信息
      const userResponse = await authApi.getCurrentUser()
      setUser(userResponse.data)

      // 恢复最近会话（若无则新建）
      await resumeOrCreateSession()

      return { success: true }
    } catch (err) {
      error.value = err.response?.data?.detail || '登录失败'
      return { success: false, error: error.value }
    } finally {
      isLoading.value = false
    }
  }

  // 快速登录（仅用户名）
  const quickLogin = async (username) => {
    isLoading.value = true
    error.value = null

    try {
      clearAuth()
      const response = await authApi.quickLogin(username)

      // 设置令牌
      setTokens(response.data.access_token, response.data.refresh_token)

      // 获取用户信息
      const userResponse = await authApi.getCurrentUser()
      setUser(userResponse.data)

      // 恢复最近会话（若无则新建）
      await resumeOrCreateSession()

      return { success: true }
    } catch (err) {
      error.value = err.response?.data?.detail || '登录失败'
      return { success: false, error: error.value }
    } finally {
      isLoading.value = false
    }
  }

  // 登出
  const logout = async () => {
    isLoading.value = true

    try {
      await authApi.logout()
    } catch (err) {
      console.error('登出失败:', err)
    } finally {
      clearAuth()
      isLoading.value = false
      router.push('/login')
    }
  }

  // 刷新令牌
  const refreshAccessToken = async () => {
    if (!refreshToken.value) {
      clearAuth()
      return false
    }

    try {
      const response = await authApi.refreshToken(refreshToken.value)
      setTokens(response.data.access_token, response.data.refresh_token)
      return true
    } catch (err) {
      console.error('刷新令牌失败:', err)
      clearAuth()
      return false
    }
  }

  // 更新用户信息
  const updateProfile = async (userData) => {
    isLoading.value = true
    error.value = null

    try {
      const response = await authApi.updateProfile(userData)
      setUser(response.data)
      return { success: true, data: response.data }
    } catch (err) {
      error.value = err.response?.data?.detail || '更新失败'
      return { success: false, error: error.value }
    } finally {
      isLoading.value = false
    }
  }

  const submitOnboarding = async (answers, sessionId = '') => {
    isLoading.value = true
    error.value = null
    try {
      const response = await authApi.parseOnboarding({ answers, session_id: sessionId || undefined })
      const currentOnboarding = user.value?.settings?.ifs_onboarding || {}

      const fixedSource = Array.isArray(currentOnboarding.trauma_events_fixed) && currentOnboarding.trauma_events_fixed.length
        ? currentOnboarding.trauma_events_fixed.map((event, index) => normalizeFixedOrb({
          id: event?.event_id,
          title: event?.title,
          trigger_event: event?.trigger_event,
          trauma_text: event?.trauma_event,
          intensity: event?.intensity,
          persona_hint: event?.persona_hint,
          source_type: event?.source_type,
          created_at: event?.created_at,
          orb_rank: event?.event_rank,
        }, index))
        : currentOnboarding.memory_orbs_fixed

      const fixedOrbs = buildFixedMemoryOrbs(answers, response.data, fixedSource)
      const fixedEvents = fixedOrbs.map((orb, index) => normalizeTraumaEvent(orb, index))

      const customSource = Array.isArray(currentOnboarding.trauma_events_custom) && currentOnboarding.trauma_events_custom.length
        ? currentOnboarding.trauma_events_custom.map((event, index) => normalizeFixedOrb({
          id: event?.event_id,
          title: event?.title,
          trigger_event: event?.trigger_event,
          trauma_text: event?.trauma_event,
          intensity: event?.intensity,
          persona_hint: event?.persona_hint,
          source_type: event?.source_type,
          created_at: event?.created_at,
          orb_rank: event?.event_rank,
        }, index))
        : currentOnboarding.memory_orbs_custom

      const customOrbs = Array.isArray(customSource)
        ? customSource.map((orb, index) => normalizeFixedOrb({
          ...orb,
          source_type: orb?.source_type || 'custom',
        }, index))
        : []
      const customEvents = customOrbs.map((orb, index) => normalizeTraumaEvent({
        ...orb,
        source_type: orb?.source_type || 'custom',
      }, index))
      const nextUser = {
        ...(user.value || {}),
        settings: {
          ...(user.value?.settings || {}),
          ifs_onboarding_completed: true,
          ifs_onboarding: {
            ...currentOnboarding,
            exiles_system_prompt: response.data.exiles_system_prompt,
            firefighters_system_prompt: response.data.firefighters_system_prompt,
            trauma_hypothesis: response.data.trauma_hypothesis,
            user_core_info: response.data.user_core_info,
            core_beliefs: response.data.core_beliefs,
            profile_digest: response.data.profile_digest,
            persona_portraits: response.data.persona_portraits,
            profile_version: response.data.profile_version,
            profile_confirmed: response.data.profile_confirmed,
            trauma_events_fixed: fixedEvents,
            trauma_events_custom: customEvents,
            trauma_events_initialized: true,
            memory_orbs_fixed: fixedOrbs,
            memory_orbs_custom: customOrbs,
            memory_orbs_initialized: true,
          }
        }
      }
      try {
        const persisted = await authApi.updateProfile({ settings: nextUser.settings })
        setUser(persisted.data)
      } catch {
        setUser(nextUser)
      }
      return { success: true, data: response.data }
    } catch (err) {
      error.value = err.response?.data?.detail || '问卷提交失败'
      return { success: false, error: error.value }
    } finally {
      isLoading.value = false
    }
  }

  const getOnboardingArchives = async () => {
    try {
      const response = await authApi.getOnboardingArchives()
      return { success: true, data: response.data }
    } catch (err) {
      const message = err.response?.data?.detail || '获取人格存档失败'
      return { success: false, error: message }
    }
  }

  const restoreOnboardingArchive = async (profileVersion, sessionId = '') => {
    try {
      const response = await authApi.restoreOnboardingArchive({
        profile_version: profileVersion,
        session_id: sessionId || undefined,
      })

      const userResponse = await authApi.getCurrentUser()
      setUser(userResponse.data)
      return { success: true, data: response.data }
    } catch (err) {
      const message = err.response?.data?.detail || '恢复人格存档失败'
      return { success: false, error: message }
    }
  }

  // 初始化检查
  const initialize = async () => {
    if (token.value && !user.value) {
      // 令牌存在但用户信息丢失，尝试获取用户信息
      try {
        const response = await authApi.getCurrentUser()
        setUser(response.data)
      } catch (err) {
        console.error('初始化用户信息失败:', err)
        // 令牌可能过期，尝试刷新
        if (err.response?.status === 401) {
          const refreshed = await refreshAccessToken()
          if (refreshed) {
            // 刷新成功，重新获取用户信息
            try {
              const response = await authApi.getCurrentUser()
              setUser(response.data)
            } catch (err2) {
              console.error('重新获取用户信息失败:', err2)
              clearAuth()
            }
          }
        } else {
          clearAuth()
        }
      }
    }

    if (token.value && user.value && !currentSessionId.value) {
      await createDefaultSession()
    }
  }

  return {
    // 状态
    user,
    token,
    refreshToken,
    isLoading,
    error,
    currentSessionId,

    // 计算属性
    isAuthenticated,
    userName,
    userId,
    needsOnboarding,

    // 方法
    setTokens,
    setUser,
    clearAuth,
    setSessionId,
    createDefaultSession,
    resumeOrCreateSession,
    register,
    login,
    quickLogin,
    logout,
    refreshAccessToken,
    updateProfile,
    submitOnboarding,
    getOnboardingArchives,
    restoreOnboardingArchive,
    initialize
  }
})
