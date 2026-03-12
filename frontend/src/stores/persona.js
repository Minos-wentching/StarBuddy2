/**
 * 人格状态管理
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const usePersonaStore = defineStore('persona', () => {
  // 状态
  const currentPersona = ref('manager')
  const emotionIntensity = ref(0.0)
  const isInnerCouncilActive = ref(false)
  const personaHistory = ref([])
  const councilProgress = ref({
    councilId: null,
    currentRound: 0,
    totalRounds: 0,
    arguments: { exiles: '', firefighters: '' }
  })
  const coreBeliefs = ref([])
  const councilRounds = ref([])
  const councilConclusion = ref('')
  const selfPresenceClarity = ref(0.6)
  const selfPresenceCompassion = ref(0.6)
  const selfPresenceTrend = ref('stable')
  const selfPresenceAnalysis = ref('')

  // 人格配置
  const personas = {
    manager: {
      name: '安全岛',
      icon: 'mdi-island',
      color: 'hsl(210, 55%, 60%)',
      description: '稳定、可预测的交流基地，提供安全感'
    },
    exiles: {
      name: '感知精灵',
      icon: 'mdi-creation',
      color: 'hsl(25, 85%, 73%)',
      description: '感官敏感的自我，帮助理解感官体验'
    },
    firefighters: {
      name: '规则守卫',
      icon: 'mdi-shield-star',
      color: 'hsl(100, 40%, 65%)',
      description: '守护秩序与规律，在变化中寻找确定性'
    },
    counselor: {
      name: '星星向导',
      icon: 'mdi-star-shooting',
      color: 'hsl(260, 35%, 65%)',
      description: '帮助理解行为模式、建立自我认知'
    }
  }

  // 计算属性
  const personaDisplay = computed(() => {
    const persona = personas[currentPersona.value]
    return persona ? persona.name : currentPersona.value
  })

  const personaIcon = computed(() => {
    const persona = personas[currentPersona.value]
    return persona ? persona.icon : 'mdi-account'
  })

  const backgroundColor = computed(() => {
    const persona = personas[currentPersona.value]
    return persona ? persona.color : 'hsl(210, 80%, 50%)'
  })

  const personaDescription = computed(() => {
    const persona = personas[currentPersona.value]
    return persona ? persona.description : ''
  })

  const emotionColor = computed(() => {
    const intensity = emotionIntensity.value
    if (intensity < 0.3) return 'green'
    if (intensity < 0.7) return 'yellow'
    return 'red'
  })

  const emotionLevel = computed(() => {
    const intensity = emotionIntensity.value
    if (intensity < 0.3) return '平静'
    if (intensity < 0.7) return '中等'
    return '强烈'
  })

  // 方法
  const switchPersona = (persona, intensity, reason = '') => {
    const oldPersona = currentPersona.value
    currentPersona.value = persona
    emotionIntensity.value = intensity

    // 记录历史
    personaHistory.value.push({
      from: oldPersona,
      to: persona,
      intensity,
      reason,
      timestamp: new Date().toISOString()
    })

    // 限制历史记录长度
    if (personaHistory.value.length > 100) {
      personaHistory.value = personaHistory.value.slice(-100)
    }

  }

  const updateEmotion = (intensity, dominantEmotion = null) => {
    emotionIntensity.value = Math.max(0, Math.min(1, intensity))
  }

  const startInnerCouncil = (councilId, totalRounds = 5) => {
    isInnerCouncilActive.value = true
    councilProgress.value = {
      councilId,
      currentRound: 0,
      totalRounds,
      arguments: { exiles: '', firefighters: '' }
    }
  }

  const updateCouncilDebate = (round, args) => {
    councilProgress.value.currentRound = round
    councilProgress.value.arguments = args
  }

  const completeCouncil = (conclusion) => {
    isInnerCouncilActive.value = false
    councilProgress.value = {
      councilId: null,
      currentRound: 0,
      totalRounds: 0,
      arguments: { exiles: '', firefighters: '' }
    }

    // 议会完成，切换到counselor显示结论
    switchPersona('counselor', emotionIntensity.value, '议会完成')
  }

  const resetState = () => {
    currentPersona.value = 'manager'
    emotionIntensity.value = 0.0
    isInnerCouncilActive.value = false
    personaHistory.value = []
    councilProgress.value = {
      councilId: null,
      currentRound: 0,
      totalRounds: 0,
      arguments: { exiles: '', firefighters: '' }
    }
    coreBeliefs.value = []
    councilRounds.value = []
    councilConclusion.value = ''
    selfPresenceClarity.value = 0.6
    selfPresenceCompassion.value = 0.6
    selfPresenceTrend.value = 'stable'
    selfPresenceAnalysis.value = ''
  }

  const getPersonaHistory = (limit = 10) => {
    return personaHistory.value.slice(-limit)
  }

  const getPersonaStats = () => {
    const stats = {
      manager: 0,
      exiles: 0,
      firefighters: 0,
      counselor: 0
    }

    // 统计历史中出现的人格次数
    personaHistory.value.forEach(entry => {
      if (stats.hasOwnProperty(entry.to)) {
        stats[entry.to]++
      }
    })

    // 加上当前人格
    if (stats.hasOwnProperty(currentPersona.value)) {
      stats[currentPersona.value]++
    }

    return stats
  }

  // 从SSE事件处理
  const handlePersonaSwitchEvent = (eventData) => {
    switchPersona(
      eventData.persona,
      eventData.intensity,
      eventData.reason || 'SSE事件触发'
    )
  }

  const handleEmotionUpdateEvent = (eventData) => {
    updateEmotion(eventData.intensity, eventData.dominant_emotion)
  }

  const handleCouncilUpdateEvent = (eventData) => {
    if (!isInnerCouncilActive.value) {
      startInnerCouncil(eventData.council_id, eventData.total_rounds)
    }
    councilProgress.value.currentRound = eventData.round
    // 存储完整的轮次数据用于议会日志
    councilRounds.value.push({
      round: eventData.round,
      exiles_argument: eventData.exiles_argument || '',
      firefighters_argument: eventData.firefighters_argument || '',
      counselor_analysis: eventData.counselor_analysis || '',
      timestamp: eventData.timestamp,
    })
  }

  const handleCouncilCompleteEvent = (eventData) => {
    councilConclusion.value = eventData.conclusion || ''
    completeCouncil(eventData.conclusion)
  }

  const handleCounselorReportEvent = (eventData) => {
    coreBeliefs.value = eventData.core_beliefs || []
    const selfPresence = eventData.self_presence || {}
    if (typeof selfPresence.clarity === 'number') {
      selfPresenceClarity.value = Math.max(0, Math.min(1, selfPresence.clarity))
    }
    if (typeof selfPresence.compassion === 'number') {
      selfPresenceCompassion.value = Math.max(0, Math.min(1, selfPresence.compassion))
    }
    if (typeof selfPresence.trend === 'string') {
      selfPresenceTrend.value = selfPresence.trend
    }
    if (typeof selfPresence.analysis === 'string') {
      selfPresenceAnalysis.value = selfPresence.analysis
    }
  }

  return {
    // 状态
    currentPersona,
    emotionIntensity,
    isInnerCouncilActive,
    personaHistory,
    councilProgress,
    coreBeliefs,
    councilRounds,
    councilConclusion,
    selfPresenceClarity,
    selfPresenceCompassion,
    selfPresenceTrend,
    selfPresenceAnalysis,

    // 计算属性
    personaDisplay,
    personaIcon,
    backgroundColor,
    personaDescription,
    emotionColor,
    emotionLevel,

    // 方法
    switchPersona,
    updateEmotion,
    startInnerCouncil,
    updateCouncilDebate,
    completeCouncil,
    resetState,
    getPersonaHistory,
    getPersonaStats,
    handlePersonaSwitchEvent,
    handleEmotionUpdateEvent,
    handleCouncilUpdateEvent,
    handleCouncilCompleteEvent,
    handleCounselorReportEvent,
  }
})
