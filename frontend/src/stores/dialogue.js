/**
 * 对话状态管理
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useDialogueStore = defineStore('dialogue', () => {
  // 状态
  const messages = ref([])
  const isLoading = ref(false)
  const currentSessionId = ref('')
  const sessionStatus = ref({
    isActive: true,
    messageCount: 0,
    lastActivity: null
  })

  // 计算属性
  const messageCount = computed(() => messages.value.length)
  const lastMessage = computed(() => messages.value[messages.value.length - 1] || null)
  const lastResponse = computed(() => {
    return messages.value.findLast(msg => msg.type === 'response') ?? null
  })

  // 方法
  const addMessage = (message, type = 'user', persona = null, emotionIntensity = null, versionInfo = null) => {
    const messageObj = {
      id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      content: message,
      type,
      persona,
      emotionIntensity,
      versionInfo,
      timestamp: new Date().toISOString()
    }

    messages.value.push(messageObj)

    // 更新会话状态
    sessionStatus.value.messageCount = messages.value.length
    sessionStatus.value.lastActivity = new Date().toISOString()

    return messageObj
  }

  const addUserMessage = (message) => {
    return addMessage(message, 'user')
  }

  const addResponseMessage = (response, persona, emotionIntensity, versionInfo = null) => {
    return addMessage(response, 'response', persona, emotionIntensity, versionInfo)
  }

  const addSystemMessage = (message) => {
    return addMessage(message, 'system')
  }

  const clearMessages = () => {
    messages.value = []
    sessionStatus.value.messageCount = 0
    sessionStatus.value.lastActivity = null
  }

  const getMessages = (limit = 50, offset = 0) => {
    const start = offset
    const end = offset + limit
    return messages.value.slice(start, end)
  }

  const getMessagesByPersona = (persona) => {
    return messages.value.filter(msg => msg.persona === persona)
  }

  const getMessagesByEmotionRange = (minIntensity = 0, maxIntensity = 1) => {
    return messages.value.filter(msg => {
      const intensity = msg.emotionIntensity
      return intensity !== null && intensity >= minIntensity && intensity <= maxIntensity
    })
  }

  const getConversationHistory = (includeSystem = false) => {
    return messages.value.filter(msg => includeSystem || msg.type !== 'system')
  }

  const getEmotionTrend = () => {
    const emotionData = messages.value
      .filter(msg => msg.emotionIntensity !== null)
      .map(msg => ({
        intensity: msg.emotionIntensity,
        timestamp: msg.timestamp,
        persona: msg.persona
      }))

    return emotionData
  }

  const startNewSession = (sessionId) => {
    currentSessionId.value = sessionId
    clearMessages()
    sessionStatus.value = {
      isActive: true,
      messageCount: 0,
      lastActivity: new Date().toISOString()
    }

    // 添加欢迎消息
    addSystemMessage('新会话已开始。请分享您的感受和想法。')
  }

  const endSession = () => {
    sessionStatus.value.isActive = false
    addSystemMessage('会话已结束。')
  }

  const resumeSession = (sessionId, previousMessages) => {
    currentSessionId.value = sessionId
    messages.value = previousMessages || []
    sessionStatus.value = {
      isActive: true,
      messageCount: messages.value.length,
      lastActivity: new Date().toISOString()
    }

    addSystemMessage('会话已恢复。')
  }

  const exportConversation = (format = 'json') => {
    const data = {
      sessionId: currentSessionId.value,
      messages: messages.value,
      metadata: {
        exportDate: new Date().toISOString(),
        totalMessages: messages.value.length,
        personas: [...new Set(messages.value.map(msg => msg.persona).filter(Boolean))]
      }
    }

    switch (format) {
      case 'json':
        return JSON.stringify(data, null, 2)
      case 'text':
        return messages.value.map(msg => {
          const timestamp = new Date(msg.timestamp).toLocaleString()
          const persona = msg.persona ? `[${msg.persona}]` : ''
          return `${timestamp} ${persona}: ${msg.content}`
        }).join('\n')
      default:
        return JSON.stringify(data, null, 2)
    }
  }

  const importConversation = (data) => {
    try {
      const conversation = typeof data === 'string' ? JSON.parse(data) : data

      if (conversation.sessionId) {
        currentSessionId.value = conversation.sessionId
      }

      if (Array.isArray(conversation.messages)) {
        messages.value = conversation.messages
        sessionStatus.value.messageCount = messages.value.length
        sessionStatus.value.lastActivity = messages.value.length > 0
          ? messages.value[messages.value.length - 1].timestamp
          : new Date().toISOString()
      }

      return true
    } catch (error) {
      console.error('导入对话失败:', error)
      return false
    }
  }

  const getSessionSummary = () => {
    const userMessages = messages.value.filter(msg => msg.type === 'user').length
    const responseMessages = messages.value.filter(msg => msg.type === 'response').length
    const systemMessages = messages.value.filter(msg => msg.type === 'system').length

    const personas = {}
    messages.value.forEach(msg => {
      if (msg.persona) {
        personas[msg.persona] = (personas[msg.persona] || 0) + 1
      }
    })

    const emotionIntensities = messages.value
      .filter(msg => msg.emotionIntensity !== null)
      .map(msg => msg.emotionIntensity)

    const avgEmotion = emotionIntensities.length > 0
      ? emotionIntensities.reduce((sum, val) => sum + val, 0) / emotionIntensities.length
      : 0

    return {
      sessionId: currentSessionId.value,
      totalMessages: messages.value.length,
      userMessages,
      responseMessages,
      systemMessages,
      personas,
      averageEmotionIntensity: avgEmotion,
      duration: messages.value.length > 0
        ? (new Date() - new Date(messages.value[0].timestamp)) / (1000 * 60) // 分钟
        : 0,
      isActive: sessionStatus.value.isActive,
      lastActivity: sessionStatus.value.lastActivity
    }
  }

  return {
    // 状态
    messages,
    isLoading,
    currentSessionId,
    sessionStatus,

    // 计算属性
    messageCount,
    lastMessage,
    lastResponse,

    // 方法
    addMessage,
    addUserMessage,
    addResponseMessage,
    addSystemMessage,
    clearMessages,
    getMessages,
    getMessagesByPersona,
    getMessagesByEmotionRange,
    getConversationHistory,
    getEmotionTrend,
    startNewSession,
    endSession,
    resumeSession,
    exportConversation,
    importConversation,
    getSessionSummary
  }
})