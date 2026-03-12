/**
 * 人格映射和情绪颜色工具
 *
 * 统一管理 persona 的显示名称、图标、颜色等映射，
 * 以及情绪强度相关的颜色计算逻辑。
 *
 * 注意：颜色相关功能已迁移到设计系统 (design-system/colors.js)
 */

import { getPersonaVuetifyColor, getEmotionColor as getEmotionColorFromDesignSystem } from '@/design-system/colors'

const PERSONA_DISPLAY_MAP = {
  manager: '安全岛',
  exiles: '感知精灵',
  firefighters: '规则守卫',
  counselor: '星星向导',
}

const PERSONA_ICON_MAP = {
  manager: 'mdi-island',
  exiles: 'mdi-creation',
  firefighters: 'mdi-shield-star',
  counselor: 'mdi-star-shooting',
}

// 使用设计系统获取 Vuetify 颜色名称
const PERSONA_COLOR_MAP = {
  manager: 'blue', // 保持向后兼容，实际使用设计系统
  exiles: 'orange-lighten-2',
  firefighters: 'light-green',
  counselor: 'purple-lighten-2',
}

const PERSONA_DESCRIPTION_MAP = {
  manager: '稳定、可预测的交流基地，提供安全感。',
  exiles: '感官敏感的自我，帮助你理解感官体验。',
  firefighters: '守护秩序与规律，在变化中寻找确定性。',
  counselor: '帮助你理解行为模式、建立自我认知。',
}

export const getPersonaDisplay = (persona) =>
  PERSONA_DISPLAY_MAP[persona] || persona

export const getPersonaIcon = (persona) =>
  PERSONA_ICON_MAP[persona] || 'mdi-account'

export const getPersonaColor = (persona) =>
  getPersonaVuetifyColor(persona)

export const getPersonaDescription = (persona) =>
  PERSONA_DESCRIPTION_MAP[persona] || ''

/**
 * 根据情绪强度返回对应颜色
 * @param {number} intensity - 情绪强度 0~1
 * @returns {string} 颜色值
 */
export const getEmotionColor = (intensity) => {
  return getEmotionColorFromDesignSystem(intensity, 'hex')
}

/**
 * 根据情绪强度返回颜色名称（用于 Vuetify 组件）
 * @param {number} intensity - 情绪强度 0~1
 * @returns {string} 颜色名称
 */
export const getEmotionColorName = (intensity) => {
  return getEmotionColorFromDesignSystem(intensity, 'vuetify')
}
