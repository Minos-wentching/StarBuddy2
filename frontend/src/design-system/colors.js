/**
 * 人格颜色设计系统
 *
 * 统一管理所有人格的颜色定义，提供多种格式支持：
 * - CSS 自定义属性 (CSS custom properties)
 * - Vuetify 颜色名称 (Vuetify color names)
 * - OKLCH 颜色值 (现代色彩空间)
 * - HEX 和 RGB 传统格式
 *
 * 所有颜色应保持视觉一致性和可访问性（对比度达标）。
 */

/**
 * 人格颜色定义 - 单一事实来源
 */
export const PERSONA_COLORS = {
  manager: {
    // 核心颜色
    hex: '#5B9BD5',
    rgb: '91, 155, 213',
    oklch: 'oklch(72% 0.10 240)',
    // 衍生颜色（用于不同场景）
    light: 'oklch(85% 0.07 240)',
    dark: 'oklch(55% 0.12 240)',
    // Vuetify 映射
    vuetify: 'blue',
    // 情感属性
    emotion: 'calm',
    description: '安全岛 - 稳定、可预测的交流基地'
  },
  exiles: {
    hex: '#F4B183',
    rgb: '244, 177, 131',
    oklch: 'oklch(80% 0.12 55)',
    light: 'oklch(90% 0.08 55)',
    dark: 'oklch(65% 0.15 45)',
    vuetify: 'orange-lighten-2',
    emotion: 'sensitive',
    description: '感知精灵 - 感官敏感的自我'
  },
  firefighters: {
    hex: '#A9D18E',
    rgb: '169, 209, 142',
    oklch: 'oklch(82% 0.10 140)',
    light: 'oklch(90% 0.07 140)',
    dark: 'oklch(65% 0.12 135)',
    vuetify: 'light-green',
    emotion: 'structured',
    description: '规则守卫 - 守护秩序与规律'
  },
  counselor: {
    hex: '#B4A7D6',
    rgb: '180, 167, 214',
    oklch: 'oklch(75% 0.08 290)',
    light: 'oklch(85% 0.06 290)',
    dark: 'oklch(58% 0.10 280)',
    vuetify: 'purple-lighten-2',
    emotion: 'wise',
    description: '星星向导 - 帮助理解行为模式'
  },
  calm: {
    hex: '#95B8D1',
    rgb: '149, 184, 209',
    oklch: 'oklch(76% 0.05 230)',
    light: 'oklch(86% 0.03 230)',
    dark: 'oklch(58% 0.06 230)',
    vuetify: 'blue-grey-lighten-2',
    emotion: 'neutral',
    description: '平静状态'
  }
};

/**
 * 情绪强度颜色映射
 * 根据情绪强度返回对应的颜色
 */
export const EMOTION_INTENSITY_COLORS = {
  low: {
    hex: '#4CAF50',
    vuetify: 'green',
    threshold: 0.3
  },
  medium: {
    hex: '#FF9800',
    vuetify: 'orange',
    threshold: 0.7
  },
  high: {
    hex: '#F44336',
    vuetify: 'red',
    threshold: 1.0
  }
};

/**
 * 获取人格颜色（默认返回 HEX 格式）
 * @param {string} persona - 人格标识符
 * @param {string} format - 格式: 'hex', 'rgb', 'oklch', 'vuetify', 'light', 'dark'
 * @returns {string} 颜色值
 */
export function getPersonaColor(persona, format = 'hex') {
  const colorDef = PERSONA_COLORS[persona] || PERSONA_COLORS.manager;

  switch (format) {
    case 'hex':
      return colorDef.hex;
    case 'rgb':
      return colorDef.rgb;
    case 'oklch':
      return colorDef.oklch;
    case 'vuetify':
      return colorDef.vuetify;
    case 'light':
      return colorDef.light;
    case 'dark':
      return colorDef.dark;
    default:
      return colorDef.hex;
  }
}

/**
 * 获取 Vuetify 颜色名称（兼容现有 usePersona.js）
 * @param {string} persona - 人格标识符
 * @returns {string} Vuetify 颜色名称
 */
export function getPersonaVuetifyColor(persona) {
  return getPersonaColor(persona, 'vuetify');
}

/**
 * 获取 OKLCH 颜色（用于现代 CSS 和 Three.js）
 * @param {string} persona - 人格标识符
 * @returns {string} OKLCH 颜色值
 */
export function getPersonaOklch(persona) {
  return getPersonaColor(persona, 'oklch');
}

/**
 * 根据情绪强度获取颜色
 * @param {number} intensity - 情绪强度 0~1
 * @param {string} format - 格式: 'hex', 'vuetify'
 * @returns {string} 颜色值
 */
export function getEmotionColor(intensity, format = 'hex') {
  let level;
  if (intensity < EMOTION_INTENSITY_COLORS.low.threshold) {
    level = 'low';
  } else if (intensity < EMOTION_INTENSITY_COLORS.medium.threshold) {
    level = 'medium';
  } else {
    level = 'high';
  }

  const colorDef = EMOTION_INTENSITY_COLORS[level];
  return format === 'vuetify' ? colorDef.vuetify : colorDef.hex;
}

/**
 * 生成 CSS 自定义属性字符串
 * 可在 :root 选择器中注入，提供全局 CSS 变量
 * @returns {string} CSS 变量定义
 */
export function generateCssVariables() {
  const variables = [];

  // 人格颜色变量
  Object.entries(PERSONA_COLORS).forEach(([persona, colors]) => {
    variables.push(`--persona-${persona}: ${colors.hex};`);
    variables.push(`--persona-${persona}-rgb: ${colors.rgb};`);
    variables.push(`--persona-${persona}-oklch: ${colors.oklch};`);
    variables.push(`--persona-${persona}-light: ${colors.light};`);
    variables.push(`--persona-${persona}-dark: ${colors.dark};`);
  });

  // 情绪强度颜色变量
  Object.entries(EMOTION_INTENSITY_COLORS).forEach(([level, colors]) => {
    variables.push(`--emotion-${level}: ${colors.hex};`);
  });

  return variables.join('\n');
}

/**
 * 获取所有颜色定义的 JSON 对象（用于调试或导出）
 * @returns {Object} 完整的颜色定义对象
 */
export function getColorDefinitions() {
  return {
    personas: PERSONA_COLORS,
    emotionIntensity: EMOTION_INTENSITY_COLORS
  };
}