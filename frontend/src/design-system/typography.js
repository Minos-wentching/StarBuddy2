/**
 * 排版设计系统
 *
 * 统一管理字体、字号、字重、行高等排版属性。
 * 支持中英文混合排版的最佳实践。
 */

/**
 * 字体栈定义
 */
export const FONT_FAMILIES = {
  // 中文优先字体栈
  chinese: `-apple-system, BlinkMacSystemFont, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif`,
  // 英文优先字体栈
  english: `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif`,
  // 等宽字体
  monospace: `'SF Mono', Monaco, 'Cascadia Code', 'Courier New', monospace`,
  // 衬线字体（用于引述等特殊场景）
  serif: `Georgia, 'Times New Roman', serif`
};

/**
 * 字体大小缩放比例（基于 16px 基准）
 * 使用 CSS rem 单位，支持响应式调整
 */
export const FONT_SCALES = {
  xs: '0.75rem',    // 12px
  sm: '0.875rem',   // 14px
  base: '1rem',     // 16px
  lg: '1.125rem',   // 18px
  xl: '1.25rem',    // 20px
  '2xl': '1.5rem',  // 24px
  '3xl': '1.875rem', // 30px
  '4xl': '2.25rem',  // 36px
  '5xl': '3rem',     // 48px
  '6xl': '3.75rem'   // 60px
};

/**
 * 字重定义
 */
export const FONT_WEIGHTS = {
  thin: 100,
  light: 300,
  normal: 400,
  medium: 500,
  semibold: 600,
  bold: 700,
  black: 900
};

/**
 * 行高定义
 */
export const LINE_HEIGHTS = {
  none: 1,
  tight: 1.25,
  snug: 1.375,
  normal: 1.5,
  relaxed: 1.625,
  loose: 2
};

/**
 * 字母间距定义
 */
export const LETTER_SPACING = {
  tighter: '-0.05em',
  tight: '-0.025em',
  normal: '0',
  wide: '0.025em',
  wider: '0.05em',
  widest: '0.1em'
};

/**
 * 文本样式预设（用于不同场景）
 */
export const TEXT_STYLES = {
  // 标题样式
  heading1: {
    fontSize: FONT_SCALES['5xl'],
    fontWeight: FONT_WEIGHTS.bold,
    lineHeight: LINE_HEIGHTS.tight,
    fontFamily: FONT_FAMILIES.chinese
  },
  heading2: {
    fontSize: FONT_SCALES['4xl'],
    fontWeight: FONT_WEIGHTS.bold,
    lineHeight: LINE_HEIGHTS.tight,
    fontFamily: FONT_FAMILIES.chinese
  },
  heading3: {
    fontSize: FONT_SCALES['3xl'],
    fontWeight: FONT_WEIGHTS.semibold,
    lineHeight: LINE_HEIGHTS.snug,
    fontFamily: FONT_FAMILIES.chinese
  },
  heading4: {
    fontSize: FONT_SCALES['2xl'],
    fontWeight: FONT_WEIGHTS.semibold,
    lineHeight: LINE_HEIGHTS.snug,
    fontFamily: FONT_FAMILIES.chinese
  },
  heading5: {
    fontSize: FONT_SCALES.xl,
    fontWeight: FONT_WEIGHTS.semibold,
    lineHeight: LINE_HEIGHTS.normal,
    fontFamily: FONT_FAMILIES.chinese
  },
  heading6: {
    fontSize: FONT_SCALES.lg,
    fontWeight: FONT_WEIGHTS.semibold,
    lineHeight: LINE_HEIGHTS.normal,
    fontFamily: FONT_FAMILIES.chinese
  },

  // 正文样式
  bodyLarge: {
    fontSize: FONT_SCALES.lg,
    fontWeight: FONT_WEIGHTS.normal,
    lineHeight: LINE_HEIGHTS.relaxed,
    fontFamily: FONT_FAMILIES.chinese
  },
  body: {
    fontSize: FONT_SCALES.base,
    fontWeight: FONT_WEIGHTS.normal,
    lineHeight: LINE_HEIGHTS.relaxed,
    fontFamily: FONT_FAMILIES.chinese
  },
  bodySmall: {
    fontSize: FONT_SCALES.sm,
    fontWeight: FONT_WEIGHTS.normal,
    lineHeight: LINE_HEIGHTS.normal,
    fontFamily: FONT_FAMILIES.chinese
  },

  // 辅助文本
  caption: {
    fontSize: FONT_SCALES.sm,
    fontWeight: FONT_WEIGHTS.normal,
    lineHeight: LINE_HEIGHTS.normal,
    fontFamily: FONT_FAMILIES.english,
    color: 'var(--text-secondary)'
  },
  label: {
    fontSize: FONT_SCALES.sm,
    fontWeight: FONT_WEIGHTS.medium,
    lineHeight: LINE_HEIGHTS.normal,
    fontFamily: FONT_FAMILIES.english,
    letterSpacing: LETTER_SPACING.wide
  },

  // 特殊样式
  quote: {
    fontSize: FONT_SCALES.lg,
    fontWeight: FONT_WEIGHTS.light,
    lineHeight: LINE_HEIGHTS.loose,
    fontFamily: FONT_FAMILIES.serif,
    fontStyle: 'italic'
  },
  code: {
    fontSize: FONT_SCALES.sm,
    fontWeight: FONT_WEIGHTS.normal,
    lineHeight: LINE_HEIGHTS.normal,
    fontFamily: FONT_FAMILIES.monospace,
    backgroundColor: 'var(--bg-code)',
    padding: '0.25rem 0.5rem',
    borderRadius: '0.25rem'
  }
};

/**
 * 获取文本样式
 * @param {string} styleName - 样式名称
 * @returns {Object} 样式对象
 */
export function getTextStyle(styleName) {
  return TEXT_STYLES[styleName] || TEXT_STYLES.body;
}

/**
 * 生成排版相关的 CSS 变量
 * @returns {string} CSS 变量定义
 */
export function generateTypographyCssVariables() {
  const variables = [];

  // 字体栈变量
  Object.entries(FONT_FAMILIES).forEach(([name, stack]) => {
    variables.push(`--font-${name}: ${stack};`);
  });

  // 字号变量
  Object.entries(FONT_SCALES).forEach(([name, size]) => {
    variables.push(`--text-${name}: ${size};`);
  });

  // 字重变量
  Object.entries(FONT_WEIGHTS).forEach(([name, weight]) => {
    variables.push(`--font-weight-${name}: ${weight};`);
  });

  // 行高变量
  Object.entries(LINE_HEIGHTS).forEach(([name, height]) => {
    variables.push(`--line-height-${name}: ${height};`);
  });

  // 字母间距变量
  Object.entries(LETTER_SPACING).forEach(([name, spacing]) => {
    variables.push(`--letter-spacing-${name}: ${spacing};`);
  });

  return variables.join('\n');
}

/**
 * 应用文本样式到 CSS（用于内联样式或 CSS-in-JS）
 * @param {string} styleName - 样式名称
 * @returns {Object} CSS 样式对象
 */
export function applyTextStyle(styleName) {
  const style = getTextStyle(styleName);
  const css = {};

  if (style.fontSize) css.fontSize = style.fontSize;
  if (style.fontWeight) css.fontWeight = style.fontWeight;
  if (style.lineHeight) css.lineHeight = style.lineHeight;
  if (style.fontFamily) css.fontFamily = style.fontFamily;
  if (style.letterSpacing) css.letterSpacing = style.letterSpacing;
  if (style.fontStyle) css.fontStyle = style.fontStyle;
  if (style.color) css.color = style.color;
  if (style.backgroundColor) css.backgroundColor = style.backgroundColor;
  if (style.padding) css.padding = style.padding;
  if (style.borderRadius) css.borderRadius = style.borderRadius;

  return css;
}