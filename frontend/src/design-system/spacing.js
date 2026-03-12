/**
 * 间距设计系统
 *
 * 统一管理组件间距、边距、内边距等布局尺寸。
 * 基于 8px 网格系统，确保视觉对齐和一致性。
 */

/**
 * 基础间距单位（8px）
 * 使用 rem 单位以支持响应式调整
 */
const BASE_UNIT = '0.5rem'; // 8px (假设根字体大小为 16px)

/**
 * 间距比例尺
 * 遵循 8px 网格系统，提供一系列间距值
 */
export const SPACING_SCALE = {
  0: '0',
  0.5: `calc(${BASE_UNIT} * 0.5)`,  // 4px
  1: BASE_UNIT,                     // 8px
  1.5: `calc(${BASE_UNIT} * 1.5)`,  // 12px
  2: `calc(${BASE_UNIT} * 2)`,      // 16px
  2.5: `calc(${BASE_UNIT} * 2.5)`,  // 20px
  3: `calc(${BASE_UNIT} * 3)`,      // 24px
  3.5: `calc(${BASE_UNIT} * 3.5)`,  // 28px
  4: `calc(${BASE_UNIT} * 4)`,      // 32px
  5: `calc(${BASE_UNIT} * 5)`,      // 40px
  6: `calc(${BASE_UNIT} * 6)`,      // 48px
  7: `calc(${BASE_UNIT} * 7)`,      // 56px
  8: `calc(${BASE_UNIT} * 8)`,      // 64px
  9: `calc(${BASE_UNIT} * 9)`,      // 72px
  10: `calc(${BASE_UNIT} * 10)`,    // 80px
  12: `calc(${BASE_UNIT} * 12)`,    // 96px
  14: `calc(${BASE_UNIT} * 14)`,    // 112px
  16: `calc(${BASE_UNIT} * 16)`,    // 128px
  20: `calc(${BASE_UNIT} * 20)`,    // 160px
  24: `calc(${BASE_UNIT} * 24)`,    // 192px
  32: `calc(${BASE_UNIT} * 32)`,    // 256px
  40: `calc(${BASE_UNIT} * 40)`,    // 320px
  48: `calc(${BASE_UNIT} * 48)`,    // 384px
  56: `calc(${BASE_UNIT} * 56)`,    // 448px
  64: `calc(${BASE_UNIT} * 64)`,    // 512px
};

/**
 * 间距用途映射
 * 定义常见布局场景的标准间距
 */
export const SPACING_USAGES = {
  // 内边距（Padding）
  paddingSmall: SPACING_SCALE[2],      // 16px
  paddingMedium: SPACING_SCALE[3],     // 24px
  paddingLarge: SPACING_SCALE[4],      // 32px
  paddingXLarge: SPACING_SCALE[6],     // 48px

  // 外边距（Margin）
  marginSmall: SPACING_SCALE[2],       // 16px
  marginMedium: SPACING_SCALE[3],      // 24px
  marginLarge: SPACING_SCALE[4],       // 32px
  marginXLarge: SPACING_SCALE[6],      // 48px

  // 组件间距（Gap）
  gapSmall: SPACING_SCALE[1],          // 8px
  gapMedium: SPACING_SCALE[2],         // 16px
  gapLarge: SPACING_SCALE[3],          // 24px
  gapXLarge: SPACING_SCALE[4],         // 32px

  // 布局间距
  sectionSpacing: SPACING_SCALE[8],    // 64px
  containerPadding: SPACING_SCALE[4],  // 32px
  cardPadding: SPACING_SCALE[3],       // 24px
  buttonPadding: SPACING_SCALE[2],     // 16px
  inputPadding: SPACING_SCALE[2],      // 16px

  // 特殊间距
  borderWidth: '1px',
  borderRadiusSmall: SPACING_SCALE[0.5],  // 4px
  borderRadiusMedium: SPACING_SCALE[1],   // 8px
  borderRadiusLarge: SPACING_SCALE[1.5],  // 12px
  borderRadiusXLarge: SPACING_SCALE[2],   // 16px
};

/**
 * 获取间距值
 * @param {number|string} key - 间距键值（数字或使用映射）
 * @returns {string} 间距值
 */
export function getSpacing(key) {
  // 如果是数字键，直接返回比例尺中的值
  if (typeof key === 'number') {
    return SPACING_SCALE[key] || SPACING_SCALE[2];
  }

  // 如果是字符串键，检查是否为使用映射
  if (key in SPACING_USAGES) {
    return SPACING_USAGES[key];
  }

  // 默认为中等间距
  return SPACING_SCALE[2];
}

/**
 * 生成间距 CSS 变量
 * @returns {string} CSS 变量定义
 */
export function generateSpacingCssVariables() {
  const variables = [];

  // 比例尺变量
  Object.entries(SPACING_SCALE).forEach(([key, value]) => {
    variables.push(`--spacing-${key}: ${value};`);
  });

  // 用途变量
  Object.entries(SPACING_USAGES).forEach(([usage, value]) => {
    // 将驼峰命名转换为连字符命名
    const cssName = usage.replace(/([A-Z])/g, '-$1').toLowerCase();
    variables.push(`--${cssName}: ${value};`);
  });

  return variables.join('\n');
}

/**
 * 应用间距到 CSS 属性
 * @param {Object} spacing - 间距配置对象
 * @param {string} [spacing.m] - 外边距
 * @param {string} [spacing.mt] - 上外边距
 * @param {string} [spacing.mr] - 右外边距
 * @param {string} [spacing.mb] - 下外边距
 * @param {string} [spacing.ml] - 左外边距
 * @param {string} [spacing.mx] - 水平外边距
 * @param {string} [spacing.my] - 垂直外边距
 * @param {string} [spacing.p] - 内边距
 * @param {string} [spacing.pt] - 上内边距
 * @param {string} [spacing.pr] - 右内边距
 * @param {string} [spacing.pb] - 下内边距
 * @param {string} [spacing.pl] - 左内边距
 * @param {string} [spacing.px] - 水平内边距
 * @param {string} [spacing.py] - 垂直内边距
 * @param {string} [spacing.gap] - 间隙
 * @returns {Object} CSS 样式对象
 */
export function applySpacing(spacing) {
  const css = {};

  const map = {
    m: 'margin',
    mt: 'marginTop',
    mr: 'marginRight',
    mb: 'marginBottom',
    ml: 'marginLeft',
    mx: ['marginLeft', 'marginRight'],
    my: ['marginTop', 'marginBottom'],
    p: 'padding',
    pt: 'paddingTop',
    pr: 'paddingRight',
    pb: 'paddingBottom',
    pl: 'paddingLeft',
    px: ['paddingLeft', 'paddingRight'],
    py: ['paddingTop', 'paddingBottom'],
    gap: 'gap'
  };

  Object.entries(spacing).forEach(([key, value]) => {
    const cssKey = map[key];
    const spacingValue = getSpacing(value);

    if (Array.isArray(cssKey)) {
      cssKey.forEach(prop => {
        css[prop] = spacingValue;
      });
    } else if (cssKey) {
      css[cssKey] = spacingValue;
    }
  });

  return css;
}