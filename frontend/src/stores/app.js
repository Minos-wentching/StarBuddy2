/**
 * 全局应用状态：端角色选择（监护人端 / 用户端）
 */

import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

const STORAGE_KEY = 'app_role'

export const useAppStore = defineStore('app', () => {
  const role = ref(localStorage.getItem(STORAGE_KEY) || '')

  const isGuardian = computed(() => role.value === 'guardian')
  const isPatient = computed(() => role.value === 'patient')

  const setRole = (nextRole) => {
    role.value = nextRole || ''
    if (role.value) {
      localStorage.setItem(STORAGE_KEY, role.value)
    } else {
      localStorage.removeItem(STORAGE_KEY)
    }
  }

  const clearRole = () => setRole('')

  return { role, isGuardian, isPatient, setRole, clearRole }
})

