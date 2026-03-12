import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { demoScripts, demoSocialSeed, demoAgentReplies } from '@/constants/demoScripts'
import { dialogueApi } from '@/api/dialogue'
import { usePersonaStore } from '@/stores/persona'

function deepClone(value) {
  return JSON.parse(JSON.stringify(value))
}

function clamp(value, min = 0, max = 1) {
  const num = Number(value)
  if (!Number.isFinite(num)) return min
  return Math.max(min, Math.min(max, num))
}

function normalizeIntensity(rawValue, fallback = 0.55) {
  const num = Number(rawValue)
  if (!Number.isFinite(num)) return fallback
  if (num > 1) return clamp(num / 10)
  return clamp(num)
}

function createDefaultReportData() {
  return {
    core_beliefs: [],
    persona_portraits: {},
    council_summary: '',
    emotion_trend: [],
    self_presence: null,
    self_presence_trend: '',
    counselor_note: '',
  }
}

function buildDemoMessage(payload, type = 'response') {
  return {
    id: `demo_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`,
    content: payload?.content || '',
    type,
    persona: payload?.persona || null,
    emotionIntensity: typeof payload?.emotionIntensity === 'number' ? payload.emotionIntensity : null,
    versionInfo: payload?.versionInfo || null,
    timestamp: payload?.timestamp || new Date().toISOString(),
  }
}

function normalizeOrb(rawOrb, index = 0) {
  const title = String(rawOrb?.title || rawOrb?.belief || rawOrb?.trigger_event || '未命名记忆').trim()
  const triggerEventRaw = String(rawOrb?.triggerEvent || rawOrb?.trigger_event || '').trim()
  const triggerEvent = triggerEventRaw === '当前情绪触发' ? '' : triggerEventRaw
  const traumaText = String(
    rawOrb?.traumaText || rawOrb?.trauma_text || rawOrb?.document || rawOrb?.content || triggerEvent
  ).trim()

  return {
    id: String(rawOrb?.id || `fallback_orb_${index}`),
    title,
    traumaText,
    triggerEvent,
    intensity: normalizeIntensity(rawOrb?.intensity, 0.58),
    personaHint: String(rawOrb?.personaHint || rawOrb?.persona_hint || 'manager'),
    sourceType: String(rawOrb?.sourceType || rawOrb?.source_type || 'fallback'),
    createdAt: String(rawOrb?.createdAt || rawOrb?.created_at || new Date().toISOString()),
    orbRank: Number(rawOrb?.orbRank || rawOrb?.orb_rank || index + 1),
  }
}

function buildAssistantReply(persona, topic) {
  if (persona === 'firefighters') {
    return `我会先守住边界，避免系统被「${topic}」再度淹没。我们可以在安全里推进。`
  }
  if (persona === 'exiles') {
    return `当「${topic}」被看见时，我就不需要再独自躲起来。谢谢你愿意靠近这段感受。`
  }
  return `我们把「${topic}」放进会议桌面：先命名情绪，再选择动作。`
}

function getPersonaLabel(persona) {
  const map = {
    manager: '安全岛',
    exiles: '感知精灵',
    firefighters: '规则守卫',
    counselor: '星星向导',
  }
  return map[persona] || '安全岛'
}

function hashString(source = '') {
  let hash = 0
  const input = String(source || '')
  for (let i = 0; i < input.length; i += 1) {
    hash = (hash << 5) - hash + input.charCodeAt(i)
    hash |= 0
  }
  return Math.abs(hash)
}

function pickByHash(items, seed) {
  if (!Array.isArray(items) || !items.length) return ''
  const index = hashString(seed) % items.length
  return items[index]
}

function buildSeedDialogueFromScenes(script, seedIntensity = 0.55, limit = 16) {
  const messages = []
  const scenes = Array.isArray(script?.scenes) ? script.scenes : []

  for (const scene of scenes) {
    if (messages.length >= limit) break
    const payload = scene?.payload || {}

    if (scene.type === 'user_message' && payload.content) {
      messages.push(buildDemoMessage({ content: String(payload.content) }, 'user'))
      continue
    }

    if (scene.type === 'assistant_message' && payload.content) {
      messages.push(
        buildDemoMessage({
          persona: payload.persona || 'manager',
          emotionIntensity: normalizeIntensity(payload.emotionIntensity, seedIntensity),
          content: String(payload.content),
        }, 'response')
      )
      continue
    }

    if (scene.type === 'persona_switch' && payload.persona) {
      const intensity = normalizeIntensity(payload.intensity, seedIntensity)
      messages.push(
        buildDemoMessage(
          {
            content: `系统切换到 ${getPersonaLabel(payload.persona)}（强度 ${Math.round(intensity * 100)}%）`,
          },
          'system'
        )
      )
      continue
    }

    if (scene.type === 'council_round') {
      if (payload.exiles_argument) {
        messages.push(
          buildDemoMessage(
            {
              persona: 'exiles',
              emotionIntensity: clamp(seedIntensity + 0.06),
              content: String(payload.exiles_argument),
            },
            'response'
          )
        )
      }
      if (messages.length >= limit) break

      if (payload.firefighters_argument) {
        messages.push(
          buildDemoMessage(
            {
              persona: 'firefighters',
              emotionIntensity: clamp(seedIntensity + 0.08),
              content: String(payload.firefighters_argument),
            },
            'response'
          )
        )
      }
      if (messages.length >= limit) break

      if (payload.counselor_analysis) {
        messages.push(
          buildDemoMessage(
            {
              persona: 'manager',
              emotionIntensity: clamp(seedIntensity - 0.05),
              content: `星星向导纪要：${String(payload.counselor_analysis)}`,
            },
            'response'
          )
        )
      }
      continue
    }

    if (scene.type === 'council_end' && payload.conclusion) {
      messages.push(buildDemoMessage({ content: `会议结论：${String(payload.conclusion)}` }, 'system'))
      continue
    }

    if (scene.type === 'diary_update' && payload.text) {
      messages.push(
        buildDemoMessage(
          {
            persona: payload.persona || 'manager',
            emotionIntensity: clamp(seedIntensity - 0.08),
            content: `日记摘录：${String(payload.text)}`,
          },
          'response'
        )
      )
    }
  }

  return messages.slice(0, limit)
}

function buildSeedDialogueFromAnswers(answers = {}, seedPersona = 'manager', seedIntensity = 0.55) {
  const q1 = String(answers.question_1 || '').trim()
  const q2 = String(answers.question_2 || '').trim()
  const topic = q1 || q2 || '这段经历'
  const rows = []

  if (q1) rows.push(buildDemoMessage({ content: q1 }, 'user'))
  if (q2) rows.push(buildDemoMessage({ content: q2 }, 'user'))

  rows.push(
    buildDemoMessage(
      {
        persona: 'manager',
        emotionIntensity: clamp(seedIntensity),
        content: `我听到你提到了「${topic.slice(0, 24)}」。我们先把它拆成“触发-感受-动作”三段，再判断该由谁上场。`,
      },
      'response'
    )
  )
  rows.push(
    buildDemoMessage(
      {
        persona: seedPersona,
        emotionIntensity: clamp(seedIntensity + 0.06),
        content: buildAssistantReply(seedPersona, topic.slice(0, 32)),
      },
      'response'
    )
  )
  rows.push(
    buildDemoMessage(
      {
        persona: 'manager',
        emotionIntensity: clamp(seedIntensity - 0.08),
        content: '已生成预置对话样本。你可以直接触发记忆球，把这条线推进成完整议会。'
      },
      'response'
    )
  )

  return rows
}

function buildOrbDialoguePack(orb, persona, intensity, topic) {
  const seed = `${orb?.id || ''}_${topic || ''}_${persona || ''}`

  const protectorLines = [
    `我不否认痛苦，但我会先把系统从「${topic}」里拉出来，避免再次过载。`,
    `这不是逃避，是紧急保护。先稳住呼吸，再决定要不要继续暴露在压力里。`,
    `我愿意退一步，不再只靠硬扛。我们可以换成更可持续的推进方式。`,
  ]
  const exileLines = [
    `其实我真正想说的是：当「${topic}」发生时，我会立刻觉得自己不被需要。`,
    `我不是想拖后腿，我只是害怕再次经历同样的否定。`,
    `如果有人能先确认我的感受，我就不必用沉默或崩溃来求救。`,
  ]
  const managerLines = [
    `会议记录：本轮先确认情绪，再协商动作边界。目标是"既不压抑，也不过载"。`,
    `结论草案：把「${topic}」拆成可执行步骤，用节律替代冲动反应。`,
    `系统建议：把这次触发写入日记，并在下一轮复盘"什么动作真正有效"。`,
  ]

  const companionPersona = persona === 'firefighters' ? 'exiles' : 'firefighters'
  const companionLine = persona === 'firefighters'
    ? pickByHash(exileLines, `${seed}_companion`)
    : pickByHash(protectorLines, `${seed}_companion`)

  return [
    buildDemoMessage({ content: orb?.traumaText || topic }, 'user'),
    buildDemoMessage(
      {
        persona,
        emotionIntensity: intensity,
        content: buildAssistantReply(persona, topic),
      },
      'response'
    ),
    buildDemoMessage(
      {
        persona: companionPersona,
        emotionIntensity: clamp(intensity - 0.08),
        content: companionLine,
      },
      'response'
    ),
    buildDemoMessage(
      {
        persona: 'manager',
        emotionIntensity: clamp(intensity - 0.12),
        content: pickByHash(managerLines, `${seed}_manager`),
      },
      'response'
    ),
  ]
}

export const useShowcaseStore = defineStore('showcase', () => {
  const enabled = ref(import.meta.env.VITE_SHOWCASE_ENABLED !== 'false')
  const userId = ref('')
  const completed = ref(false)
  const active = ref(false)
  const currentScriptId = ref(demoScripts[0]?.id || '')

  const demoMessages = ref([])
  const narrativeChapters = ref([])
  const reportData = ref(createDefaultReportData())
  const socialData = ref(deepClone(demoSocialSeed))

  const memoryOrbs = ref([])
  const lockedMemoryOrbs = ref([])
  const selectedOrbId = ref('')
  const manualSwitchEvents = ref([])
  const lastCouncilTopic = ref('')
  const qaAnswers = ref({ question_1: '', question_2: '' })

  const scripts = ref(demoScripts)

  const currentScript = computed(() => {
    const hit = scripts.value.find((item) => item.id === currentScriptId.value)
    return hit || scripts.value[0] || null
  })

  const completionKey = (uid) => `showcase_completed_u${uid}`

  function bindUser(nextUserId) {
    userId.value = String(nextUserId || '')
    if (!userId.value) {
      completed.value = false
      return
    }
    completed.value = localStorage.getItem(completionKey(userId.value)) === '1'
  }

  function markCompleted(value = true) {
    completed.value = Boolean(value)
    if (!userId.value) return
    if (completed.value) {
      localStorage.setItem(completionKey(userId.value), '1')
    } else {
      localStorage.removeItem(completionKey(userId.value))
    }
  }

  function setAnswers(answers = {}) {
    qaAnswers.value = {
      question_1: String(answers.question_1 || '').trim(),
      question_2: String(answers.question_2 || '').trim(),
    }
  }

  function resetDemoData() {
    demoMessages.value = []
    narrativeChapters.value = []
    reportData.value = createDefaultReportData()
    socialData.value = deepClone(demoSocialSeed)
    memoryOrbs.value = []
    selectedOrbId.value = ''
    manualSwitchEvents.value = []
    lastCouncilTopic.value = ''
    qaAnswers.value = { question_1: '', question_2: '' }
  }

  function setLockedMemoryOrbs(orbs = []) {
    const list = Array.isArray(orbs) ? orbs : []
    lockedMemoryOrbs.value = list.map((orb, index) => normalizeOrb(orb, index))
  }

  function dispatchDiaryUpdate(payload) {
    if (typeof window === 'undefined' || !payload) return
    window.dispatchEvent(new CustomEvent('starbuddy:diary-update', { detail: payload }))
  }

  function updateReportHint(payload) {
    if (!payload || typeof payload !== 'object') return
    reportData.value = {
      ...reportData.value,
      ...payload,
      persona_portraits: {
        ...(reportData.value.persona_portraits || {}),
        ...(payload.persona_portraits || {}),
      },
    }
  }

  function pushNarrativeChapter(payload) {
    if (!payload?.content) return
    const exists = narrativeChapters.value.some(
      (chapter) => chapter.title === payload.title && chapter.content === payload.content
    )
    if (!exists) {
      narrativeChapters.value.push({
        title: payload.title || `第 ${narrativeChapters.value.length + 1} 章`,
        content: payload.content,
        image_url: payload.image_url || '',
      })
    }
  }

  function updateSocialHint(payload) {
    if (!payload || typeof payload !== 'object') return
    socialData.value = {
      ...socialData.value,
      ...payload,
      similarUsers: payload.similarUsers || socialData.value.similarUsers,
      myBottles: payload.myBottles || socialData.value.myBottles,
      pickedBottle: payload.pickedBottle || socialData.value.pickedBottle,
    }
  }

  function collectScriptHints(script) {
    for (const scene of script?.scenes || []) {
      if (scene.type === 'report_hint' || scene.type === 'counselor_report') {
        updateReportHint(scene.payload || {})
      }
      if (scene.type === 'narrative_chapter') {
        pushNarrativeChapter(scene.payload || {})
      }
      if (scene.type === 'social_hint') {
        updateSocialHint(scene.payload || {})
      }
    }

    if (!narrativeChapters.value.length && script?.theme) {
      pushNarrativeChapter({
        title: `${script.title} · 导览序章`,
        content: `请点击中央记忆球，手动触发伙伴转换与会议主题。`,
      })
    }
  }

  function buildFallbackOrbs(script) {
    const fromSeed = (script?.memoryOrbSeed || []).map((orb, index) => normalizeOrb(orb, index))
    if (fromSeed.length) return fromSeed

    const beliefs = []
    for (const scene of script?.scenes || []) {
      if (scene.type !== 'counselor_report') continue
      const coreBeliefs = Array.isArray(scene.payload?.core_beliefs) ? scene.payload.core_beliefs : []
      for (const belief of coreBeliefs) {
        beliefs.push({
          id: String(belief.belief_id || `${script.id}_${beliefs.length}`),
          title: String(belief.content || '核心信念'),
          trauma_text: String(scene.payload?.trigger_event || belief.origin_event || belief.content || ''),
          trigger_event: String(scene.payload?.trigger_event || belief.origin_event || belief.content || ''),
          intensity: Number(belief.intensity || 6) / 10,
          persona_hint: Number(belief.valence || 0) < -0.2 ? 'firefighters' : 'manager',
          source_type: 'script_fallback',
        })
      }
    }

    if (beliefs.length) {
      return beliefs.slice(0, 8).map((belief, index) => normalizeOrb(belief, index))
    }

    return [
      normalizeOrb({
        id: `${script?.id || 'default'}_orb_default`,
        title: script?.title || '默认记忆球',
        trauma_text: script?.theme || '从一次触发事件开始，手动推进内在对话。',
        trigger_event: script?.personaSeed?.council_topic || '本轮会议主题',
        intensity: script?.personaSeed?.intensity || 0.6,
        persona_hint: script?.personaSeed?.persona || 'manager',
        source_type: 'script_default',
      }),
    ]
  }

  async function loadMemoryOrbs(sessionId = '') {
    if (lockedMemoryOrbs.value.length) {
      memoryOrbs.value = lockedMemoryOrbs.value.map((orb, index) => normalizeOrb(orb, index))
      return memoryOrbs.value
    }

    const fallback = buildFallbackOrbs(currentScript.value)
    if (!sessionId) {
      memoryOrbs.value = fallback
      return fallback
    }

    try {
      const response = await dialogueApi.getMemoryOrbs(sessionId)
      const rawOrbs = Array.isArray(response.data?.orbs) ? response.data.orbs : []
      const normalized = rawOrbs.map((orb, index) => normalizeOrb(orb, index)).filter((orb) => orb.title)
      memoryOrbs.value = normalized.length ? normalized : fallback
      return memoryOrbs.value
    } catch (error) {
      console.warn('加载记忆球失败，使用预制数据:', error)
      memoryOrbs.value = fallback
      return fallback
    }
  }

  function appendEmotionPoint(intensity) {
    const trend = Array.isArray(reportData.value.emotion_trend) ? [...reportData.value.emotion_trend] : []
    trend.push(clamp(intensity))
    return trend.slice(-12)
  }

  function activateMemoryOrb(orb) {
    if (!active.value) return

    const normalized = normalizeOrb(orb, manualSwitchEvents.value.length)
    memoryOrbs.value = memoryOrbs.value.filter((item) => String(item.id) !== String(normalized.id))
    selectedOrbId.value = normalized.id
    lastCouncilTopic.value = normalized.triggerEvent || normalized.title

    const personaStore = usePersonaStore()
    const persona = normalized.personaHint || currentScript.value?.personaSeed?.persona || 'manager'
    const intensity = normalizeIntensity(normalized.intensity, 0.58)

    personaStore.switchPersona(persona, intensity, 'manual_memory_orb')

    manualSwitchEvents.value.push({
      orbId: normalized.id,
      persona,
      topic: lastCouncilTopic.value,
      intensity,
      timestamp: new Date().toISOString(),
    })
    if (manualSwitchEvents.value.length > 20) {
      manualSwitchEvents.value = manualSwitchEvents.value.slice(-20)
    }

    demoMessages.value.push(
      buildDemoMessage({ content: `记忆球「${normalized.title}」已唤醒，会议主题：${lastCouncilTopic.value}` }, 'system')
    )
    demoMessages.value.push(
      ...buildOrbDialoguePack(normalized, persona, intensity, lastCouncilTopic.value)
    )

    dispatchDiaryUpdate({
      persona,
      text: `当我触碰「${normalized.title}」时，我看见了：${normalized.traumaText}`,
    })

    const currentBeliefs = Array.isArray(reportData.value.core_beliefs) ? [...reportData.value.core_beliefs] : []
    const beliefExists = currentBeliefs.some((belief) => belief.content === normalized.title)
    if (!beliefExists) {
      currentBeliefs.push({
        belief_id: `orb_${normalized.id}`,
        content: normalized.title,
        valence: persona === 'firefighters' ? -0.55 : -0.25,
        intensity: Number((intensity * 10).toFixed(1)),
        origin_event: normalized.triggerEvent,
      })
    }

    updateReportHint({
      core_beliefs: currentBeliefs,
      council_summary: `手动会议主题：${lastCouncilTopic.value}`,
      emotion_trend: appendEmotionPoint(intensity),
      self_presence:
        typeof reportData.value.self_presence === 'number'
          ? clamp(reportData.value.self_presence + 0.03)
          : 0.58,
      self_presence_trend: '持续提升中',
      counselor_note: `你主动唤醒了关键记忆「${normalized.title}」，系统正在从被动反应切换为主动整合。`,
    })

    pushNarrativeChapter({
      title: `记忆球 · ${normalized.title}`,
      content: `当「${normalized.title}」被触碰，系统把「${lastCouncilTopic.value}」推上会议桌面。${buildAssistantReply(persona, lastCouncilTopic.value)}`,
    })
  }

  function startDemo(scriptId = currentScriptId.value, options = {}) {
    if (!enabled.value) return

    const targetScript = scripts.value.find((item) => item.id === scriptId) || scripts.value[0]
    if (!targetScript) return

    active.value = true
    currentScriptId.value = targetScript.id

    const personaStore = usePersonaStore()
    personaStore.resetState()
    resetDemoData()

    const incomingAnswers = options.answers || targetScript.presetAnswers || {}
    setAnswers(incomingAnswers)

    const seedPersona = targetScript.personaSeed?.persona || 'manager'
    const seedIntensity = normalizeIntensity(targetScript.personaSeed?.intensity, 0.45)
    personaStore.switchPersona(seedPersona, seedIntensity, 'showcase_seed')

    collectScriptHints(targetScript)
    updateReportHint({ emotion_trend: [seedIntensity] })

    demoMessages.value.push(
      buildDemoMessage({ content: `已进入「${targetScript.title}」。点击中央记忆球，手动触发伙伴切换与会议主题。` }, 'system')
    )

    const seededFromScenes = buildSeedDialogueFromScenes(targetScript, seedIntensity, 16)
    if (seededFromScenes.length > 0) {
      demoMessages.value.push(
        buildDemoMessage({ content: '已加载预置对话片段，你可以直接继续触发记忆球。' }, 'system')
      )
      demoMessages.value.push(...seededFromScenes)
    } else {
      demoMessages.value.push(...buildSeedDialogueFromAnswers(incomingAnswers, seedPersona, seedIntensity))
    }

    const sessionId = String(options.sessionId || options.session_id || '')
    void loadMemoryOrbs(sessionId)
  }

  function stopDemo() {
    active.value = false
    resetDemoData()
  }

  function switchScript(scriptId, options = {}) {
    if (!scripts.value.some((item) => item.id === scriptId)) return
    if (active.value && currentScriptId.value === scriptId && !options.force) return
    startDemo(scriptId, {
      ...options,
      answers: options.answers || qaAnswers.value,
    })
  }

  function mockAgentReply(agent, text = '') {
    const content = String(text || '')
    const profileKind = String(agent?.profile_kind || '')
    const beliefText = Array.isArray(agent?.shared_beliefs) ? agent.shared_beliefs.join(' ') : ''
    let pool = demoAgentReplies.default

    if (profileKind === 'guide' && /温暖|陪伴|抚慰/.test(beliefText)) {
      pool = demoAgentReplies.warm
    } else if (/真相|探索|智慧|洞察/.test(beliefText)) {
      pool = demoAgentReplies.deep
    } else if (/成长|坚韧|力量|稳定/.test(beliefText)) {
      pool = demoAgentReplies.rational
    }

    if (/害怕|焦虑|紧张|怕/.test(content)) {
      return '你能把“害怕”说出来已经很关键。我们先让身体慢下来，再决定下一步。'
    }
    if (/关系|争吵|冷战|沟通/.test(content)) {
      return '也许可以先说情绪，再说需求。这样你们讨论的是同一件事，而不是彼此防御。'
    }
    if (/不够好|失败|完美/.test(content)) {
      return '你可以继续追求成长，但不必再靠羞辱自己来前进。'
    }

    return pool[Math.floor(Math.random() * pool.length)]
  }

  return {
    enabled,
    userId,
    completed,
    active,
    scripts,
    currentScriptId,
    currentScript,

    demoMessages,
    narrativeChapters,
    reportData,
    socialData,
    memoryOrbs,
    selectedOrbId,
    manualSwitchEvents,
    lastCouncilTopic,
    qaAnswers,

    bindUser,
    markCompleted,
    setAnswers,
    startDemo,
    stopDemo,
    switchScript,
    loadMemoryOrbs,
    setLockedMemoryOrbs,
    activateMemoryOrb,
    mockAgentReply,
  }
})
