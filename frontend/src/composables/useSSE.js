/**
 * SSE (Server-Sent Events) 连接管理
 */

import { ref, watch, unref, onUnmounted } from 'vue'
import { usePersonaStore } from '@/stores/persona'
import { useDialogueStore } from '@/stores/dialogue'
import { useVersionStore } from '@/stores/version'
import { useAuthStore } from '@/stores/auth'

export function useSSE(sessionId) {
  const personaStore = usePersonaStore()
  const dialogueStore = useDialogueStore()
  const versionStore = useVersionStore()
  const authStore = useAuthStore()

  const eventSource = ref(null)
  const connected = ref(false)
  const retryCount = ref(0)
  const lastEventTime = ref(null)
  const error = ref(null)
  let reconnectTimer = null
  let healthCheckInterval = null

  const MAX_RETRIES = 10

  const resolveSessionId = () => {
    if (typeof sessionId === 'function') {
      return sessionId()
    }
    return unref(sessionId)
  }

  const resolveToken = () => {
    const rawToken = unref(authStore.token) || ''
    return rawToken.startsWith('Bearer ') ? rawToken.slice(7) : rawToken
  }

  let lastAuthOkToken = ''
  let lastAuthOkAt = 0

  const clearAuthAndRedirect = () => {
    try {
      if (typeof authStore.clearAuth === 'function') {
        authStore.clearAuth()
      } else {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        localStorage.removeItem('user')
        localStorage.removeItem('current_session_id')
      }
    } finally {
      window.location.href = '/login'
    }
  }

  const preflightAuth = async (token) => {
    if (!token) return false

    const now = Date.now()
    if (token === lastAuthOkToken && now - lastAuthOkAt < 30000) {
      return true
    }

    const fetchMe = async (accessToken) =>
      fetch('/api/auth/me', { headers: { 'X-Auth-Token': accessToken } })

    try {
      const meRes = await fetchMe(token)
      if (meRes.ok) {
        lastAuthOkToken = token
        lastAuthOkAt = Date.now()
        return true
      }

      if (meRes.status !== 401) {
        // Non-auth errors should not block SSE; the SSE endpoint may still work.
        return true
      }

      const rt = localStorage.getItem('refresh_token') || ''
      if (!rt) {
        clearAuthAndRedirect()
        return false
      }

      const refreshRes = await fetch('/api/auth/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: rt })
      })

      if (!refreshRes.ok) {
        clearAuthAndRedirect()
        return false
      }

      const refreshData = await refreshRes.json().catch(() => ({}))
      const nextAccess = refreshData?.access_token || ''
      const nextRefresh = refreshData?.refresh_token || ''

      if (!nextAccess) {
        clearAuthAndRedirect()
        return false
      }

      if (typeof authStore.setTokens === 'function') {
        authStore.setTokens(nextAccess, nextRefresh)
      } else {
        localStorage.setItem('access_token', nextAccess)
        if (nextRefresh) localStorage.setItem('refresh_token', nextRefresh)
      }

      const meRes2 = await fetchMe(nextAccess)
      if (!meRes2.ok) {
        clearAuthAndRedirect()
        return false
      }

      lastAuthOkToken = nextAccess
      lastAuthOkAt = Date.now()
      return true
    } catch (e) {
      // Network errors: don't hard block SSE.
      return true
    }
  }

  // SSE事件处理器映射
  const eventHandlers = {
    connected: (data) => {
      connected.value = true
      retryCount.value = 0
      error.value = null
    },

    heartbeat: (data) => {
      lastEventTime.value = new Date()
    },

    persona_switch: (data) => {
      personaStore.handlePersonaSwitchEvent(data)
    },

    emotion_update: (data) => {
      personaStore.handleEmotionUpdateEvent(data)
    },

    council_update: (data) => {
      personaStore.handleCouncilUpdateEvent(data)
    },

    council_complete: (data) => {
      personaStore.handleCouncilCompleteEvent(data)
    },

    counselor_report: (data) => {
      personaStore.handleCounselorReportEvent(data)
    },

    snapshot_created: (data) => {
      versionStore.addSnapshot(data)
      dialogueStore.addSystemMessage(`版本快照已创建: ${data.id?.substring(0, 8)}...`)
    },

    manager_decision: (data) => {
      const target = data?.target_agent || 'unknown'
      dialogueStore.addSystemMessage(`内在调度完成：目标人格 ${target}`)
    },

    diary_update: (data) => {
      const persona = data?.persona || 'unknown'
      dialogueStore.addSystemMessage(`新的内在日记已生成（${persona}）`)
      window.dispatchEvent(new CustomEvent('starbuddy:diary-update', { detail: data || {} }))
    },

    feedback_triggered_switch: (data) => {
      const target = data?.target_agent || 'manager'
      const intensity = Number(data?.intensity || 0)
      personaStore.switchPersona(target, intensity, '反馈触发切换')
      dialogueStore.addSystemMessage(`反馈触发伙伴切换：${target}`)
      window.dispatchEvent(new CustomEvent('starbuddy:feedback-switch', { detail: data || {} }))
    },

    error: (data) => {
      console.error('SSE服务器错误:', data)
      error.value = data.message || 'SSE连接错误'
    }
  }

  // Helper to register a named SSE event listener
  const registerEvent = (es, eventName) => {
    es.addEventListener(eventName, (event) => {
      try {
        const data = JSON.parse(event.data)
        lastEventTime.value = new Date()
        if (eventHandlers[eventName]) {
          eventHandlers[eventName](data)
        }
      } catch (e) {
        console.error(`处理${eventName}事件失败:`, e)
      }
    })
  }

  const connect = (targetSessionId = resolveSessionId()) => {
    void connectAsync(targetSessionId)
  }

  const connectAsync = async (targetSessionId = resolveSessionId()) => {
    if (!targetSessionId) {
      return
    }

    // 关闭已有连接
    disconnect()

    const token = resolveToken()
    if (!token) {
      return
    }

    const ok = await preflightAuth(token)
    if (!ok) return

    const url = `/api/sse/${targetSessionId}?token=${encodeURIComponent(token)}`

    try {
      const es = new EventSource(url)
      eventSource.value = es

      es.onopen = () => {
        connected.value = true
        retryCount.value = 0
        error.value = null
        lastEventTime.value = new Date()
      }

      // Generic message handler (fallback for unnamed events)
      es.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          lastEventTime.value = new Date()
          if (data.event_type && eventHandlers[data.event_type]) {
            eventHandlers[data.event_type](data)
          }
        } catch (parseError) {
          console.error('解析SSE消息失败:', parseError, event.data)
        }
      }

      // Register all named event listeners
      const eventNames = [
        'connected', 'heartbeat', 'persona_switch', 'emotion_update',
        'council_update', 'council_complete', 'counselor_report',
        'snapshot_created', 'manager_decision', 'diary_update',
        'feedback_triggered_switch', 'error'
      ]
      eventNames.forEach(name => registerEvent(es, name))

      // Error handling
      es.onerror = (errorEvent) => {
        console.error('SSE连接错误, readyState:', es.readyState)

        es.close()
        eventSource.value = null
        connected.value = false

        if (retryCount.value < MAX_RETRIES) {
          retryCount.value++
          const delay = Math.min(2000 * Math.pow(1.5, retryCount.value), 30000)
          error.value = null

          reconnectTimer = setTimeout(() => {
            const sid = resolveSessionId()
            if (sid && !connected.value) {
              connect(sid)
            }
          }, delay)
        } else {
          error.value = '连接失败，请刷新页面'
        }
      }

    } catch (err) {
      console.error('创建SSE连接失败:', err)
      error.value = err.message
      connected.value = false
    }
  }

  const disconnect = () => {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    if (healthCheckInterval) {
      clearInterval(healthCheckInterval)
      healthCheckInterval = null
    }
    if (eventSource.value) {
      eventSource.value.close()
      eventSource.value = null
      connected.value = false
    }
  }

  const sendTestEvent = async (eventType, data) => {
    const targetSessionId = resolveSessionId()
    if (!connected.value || !targetSessionId) return false

    try {
      const token = resolveToken()
      let url = `/api/sse/${targetSessionId}/${eventType}`
      if (token) url += `?token=${encodeURIComponent(token)}`

      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      })
      return response.ok
    } catch (err) {
      console.error('发送测试事件失败:', err)
      return false
    }
  }

  const getConnectionStatus = () => ({
    connected: connected.value,
    retryCount: retryCount.value,
    lastEvent: lastEventTime.value,
    error: error.value,
    sessionId: resolveSessionId()
  })

  // Health check: detect stale connections
  const startHealthCheck = (interval = 45000) => {
    if (healthCheckInterval) clearInterval(healthCheckInterval)
    healthCheckInterval = setInterval(() => {
      if (connected.value && lastEventTime.value) {
        const timeSinceLastEvent = new Date() - lastEventTime.value
        if (timeSinceLastEvent > 90000) {
          retryCount.value = 0
          disconnect()
          connect()
        }
      }
    }, interval)
  }

  watch(() => resolveSessionId(), (newSessionId, oldSessionId) => {
    if (!newSessionId) {
      disconnect()
      return
    }
    if (newSessionId !== oldSessionId) {
      retryCount.value = 0
      connect(newSessionId)
      startHealthCheck()
      return
    }
    if (!eventSource.value) {
      connect(newSessionId)
      startHealthCheck()
    }
  }, { immediate: true })

  watch(() => resolveToken(), (newToken, oldToken) => {
    if (newToken && newToken !== oldToken && resolveSessionId()) {
      retryCount.value = 0
      connect(resolveSessionId())
    }
  })

  onUnmounted(() => {
    disconnect()
    if (healthCheckInterval) clearInterval(healthCheckInterval)
  })

  return {
    connected,
    error,
    connect,
    disconnect,
    sendTestEvent,
    getConnectionStatus,
    startHealthCheck
  }
}
