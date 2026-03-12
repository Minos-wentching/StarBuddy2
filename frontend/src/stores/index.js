/**
 * Pinia stores 入口文件
 */

import { createPinia } from 'pinia'

// 创建Pinia实例
const pinia = createPinia()

export default pinia

// 导出所有store
export { useAuthStore } from './auth.js'
export { usePersonaStore } from './persona.js'
export { useDialogueStore } from './dialogue.js'
export { useVersionStore } from './version.js'
export { useShowcaseStore } from './showcase.js'
