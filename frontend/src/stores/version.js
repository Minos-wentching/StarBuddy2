/**
 * 版本存档状态管理
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useVersionStore = defineStore('version', () => {
  // 状态
  const snapshots = ref([])
  const currentBranch = ref('main')
  const branches = ref({
    main: [],
    emotional: [],
    insights: []
  })
  const isLoading = ref(false)

  // 计算属性
  const snapshotCount = computed(() => snapshots.value.length)
  const latestSnapshot = computed(() => snapshots.value[snapshots.value.length - 1] || null)
  const branchSnapshots = computed(() => {
    return branches.value[currentBranch.value] || []
  })

  // 方法
  const addSnapshot = (snapshotData) => {
    const snapshot = {
      id: snapshotData.id || `snapshot_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      sessionId: snapshotData.sessionId,
      stateData: snapshotData.stateData,
      metadata: snapshotData.metadata || {},
      persona: snapshotData.persona || 'unknown',
      emotionIntensity: snapshotData.emotionIntensity || 0,
      messageCount: snapshotData.messageCount || 0,
      tags: snapshotData.tags || [],
      createdAt: snapshotData.createdAt || new Date().toISOString(),
      parentHash: snapshotData.parentHash || null
    }

    snapshots.value.push(snapshot)

    // 添加到当前分支
    if (!branches.value[currentBranch.value]) {
      branches.value[currentBranch.value] = []
    }
    branches.value[currentBranch.value].push(snapshot.id)

    return snapshot
  }

  const getSnapshot = (snapshotId) => {
    return snapshots.value.find(s => s.id === snapshotId) || null
  }

  const getSnapshots = (filters = {}) => {
    let filtered = [...snapshots.value]

    // 应用过滤器
    if (filters.persona) {
      filtered = filtered.filter(s => s.persona === filters.persona)
    }

    if (filters.minIntensity !== undefined) {
      filtered = filtered.filter(s => s.emotionIntensity >= filters.minIntensity)
    }

    if (filters.maxIntensity !== undefined) {
      filtered = filtered.filter(s => s.emotionIntensity <= filters.maxIntensity)
    }

    if (filters.tags && filters.tags.length > 0) {
      filtered = filtered.filter(s => {
        return filters.tags.every(tag => s.tags.includes(tag))
      })
    }

    if (filters.limit) {
      filtered = filtered.slice(-filters.limit)
    }

    return filtered
  }

  const getSnapshotsByPersona = (persona) => {
    return snapshots.value.filter(s => s.persona === persona)
  }

  const getSnapshotsByEmotionRange = (minIntensity = 0, maxIntensity = 1) => {
    return snapshots.value.filter(s => {
      return s.emotionIntensity >= minIntensity && s.emotionIntensity <= maxIntensity
    })
  }

  const getSnapshotsByTag = (tag) => {
    return snapshots.value.filter(s => s.tags.includes(tag))
  }

  const getVersionTree = () => {
    // 构建树形结构
    const tree = {
      nodes: {},
      edges: []
    }

    snapshots.value.forEach(snapshot => {
      tree.nodes[snapshot.id] = {
        id: snapshot.id,
        persona: snapshot.persona,
        emotionIntensity: snapshot.emotionIntensity,
        messageCount: snapshot.messageCount,
        tags: snapshot.tags,
        createdAt: snapshot.createdAt
      }

      if (snapshot.parentHash && tree.nodes[snapshot.parentHash]) {
        tree.edges.push({
          from: snapshot.parentHash,
          to: snapshot.id,
          type: 'parent'
        })
      }
    })

    return tree
  }

  const createBranch = (branchName, fromSnapshotId = null) => {
    if (branches.value[branchName]) {
      throw new Error(`分支 ${branchName} 已存在`)
    }

    branches.value[branchName] = []

    if (fromSnapshotId) {
      // 从指定快照创建分支
      const snapshot = getSnapshot(fromSnapshotId)
      if (snapshot) {
        // 复制快照到新分支
        const branchSnapshot = {
          ...snapshot,
          id: `branch_${branchName}_${snapshot.id}`,
          parentHash: snapshot.id
        }
        addSnapshot(branchSnapshot)
      }
    }

    return branchName
  }

  const switchBranch = (branchName) => {
    if (!branches.value[branchName]) {
      throw new Error(`分支 ${branchName} 不存在`)
    }

    currentBranch.value = branchName
    return branchName
  }

  const mergeBranch = (sourceBranch, targetBranch = 'main') => {
    if (!branches.value[sourceBranch] || !branches.value[targetBranch]) {
      throw new Error('分支不存在')
    }

    // 合并快照ID（去重）
    const sourceIds = branches.value[sourceBranch]
    const targetIds = branches.value[targetBranch]

    const mergedIds = [...new Set([...targetIds, ...sourceIds])]
    branches.value[targetBranch] = mergedIds

    return mergedIds
  }

  const deleteSnapshot = (snapshotId) => {
    const index = snapshots.value.findIndex(s => s.id === snapshotId)
    if (index !== -1) {
      snapshots.value.splice(index, 1)

      // 从所有分支中移除
      Object.keys(branches.value).forEach(branch => {
        const branchIndex = branches.value[branch].indexOf(snapshotId)
        if (branchIndex !== -1) {
          branches.value[branch].splice(branchIndex, 1)
        }
      })

      return true
    }
    return false
  }

  const restoreSnapshot = (snapshotId) => {
    const snapshot = getSnapshot(snapshotId)
    if (!snapshot) {
      return null
    }

    // 创建恢复点
    const restorePoint = {
      ...snapshot,
      id: `restore_${Date.now()}_${snapshot.id}`,
      parentHash: snapshot.id,
      tags: [...snapshot.tags, 'restore-point'],
      createdAt: new Date().toISOString()
    }

    addSnapshot(restorePoint)
    return restorePoint
  }

  const getTimeline = () => {
    return snapshots.value
      .map(s => ({
        id: s.id,
        timestamp: new Date(s.createdAt).getTime(),
        persona: s.persona,
        emotionIntensity: s.emotionIntensity,
        tags: s.tags,
        branch: Object.keys(branches.value).find(branch =>
          branches.value[branch].includes(s.id)
        ) || 'unknown'
      }))
      .sort((a, b) => a.timestamp - b.timestamp)
  }

  const getStatistics = () => {
    const stats = {
      totalSnapshots: snapshots.value.length,
      byPersona: {},
      byEmotionLevel: {
        low: 0,    // 0-0.3
        medium: 0, // 0.3-0.7
        high: 0    // 0.7-1
      },
      byTag: {},
      branches: Object.keys(branches.value).length,
      timelineSpan: 0
    }

    // 统计人格分布
    snapshots.value.forEach(s => {
      stats.byPersona[s.persona] = (stats.byPersona[s.persona] || 0) + 1

      // 情绪水平统计
      if (s.emotionIntensity < 0.3) stats.byEmotionLevel.low++
      else if (s.emotionIntensity < 0.7) stats.byEmotionLevel.medium++
      else stats.byEmotionLevel.high++

      // 标签统计
      s.tags.forEach(tag => {
        stats.byTag[tag] = (stats.byTag[tag] || 0) + 1
      })
    })

    // 时间跨度
    if (snapshots.value.length > 0) {
      const first = new Date(snapshots.value[0].createdAt)
      const last = new Date(snapshots.value[snapshots.value.length - 1].createdAt)
      stats.timelineSpan = Math.round((last - first) / (1000 * 60 * 60)) // 小时
    }

    return stats
  }

  const exportData = (format = 'json') => {
    const data = {
      snapshots: snapshots.value,
      branches: branches.value,
      currentBranch: currentBranch.value,
      metadata: {
        exportDate: new Date().toISOString(),
        totalSnapshots: snapshots.value.length
      }
    }

    switch (format) {
      case 'json':
        return JSON.stringify(data, null, 2)
      case 'csv':
        // 简化CSV导出
        const headers = ['id', 'persona', 'emotionIntensity', 'messageCount', 'tags', 'createdAt']
        const rows = snapshots.value.map(s => [
          s.id,
          s.persona,
          s.emotionIntensity,
          s.messageCount,
          s.tags.join(';'),
          s.createdAt
        ])
        return [headers, ...rows].map(row => row.join(',')).join('\n')
      default:
        return JSON.stringify(data, null, 2)
    }
  }

  const importData = (data) => {
    try {
      const importData = typeof data === 'string' ? JSON.parse(data) : data

      if (Array.isArray(importData.snapshots)) {
        snapshots.value = importData.snapshots
      }

      if (importData.branches) {
        branches.value = importData.branches
      }

      if (importData.currentBranch) {
        currentBranch.value = importData.currentBranch
      }

      return true
    } catch (error) {
      console.error('导入版本数据失败:', error)
      return false
    }
  }

  const clearAll = () => {
    snapshots.value = []
    branches.value = { main: [] }
    currentBranch.value = 'main'
  }

  return {
    // 状态
    snapshots,
    currentBranch,
    branches,
    isLoading,

    // 计算属性
    snapshotCount,
    latestSnapshot,
    branchSnapshots,

    // 方法
    addSnapshot,
    getSnapshot,
    getSnapshots,
    getSnapshotsByPersona,
    getSnapshotsByEmotionRange,
    getSnapshotsByTag,
    getVersionTree,
    createBranch,
    switchBranch,
    mergeBranch,
    deleteSnapshot,
    restoreSnapshot,
    getTimeline,
    getStatistics,
    exportData,
    importData,
    clearAll
  }
})