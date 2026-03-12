import axios from 'axios'

const baseURL = import.meta.env.VITE_API_URL || ''
const apiClient = axios.create({
  baseURL: baseURL,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器添加token
apiClient.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers['X-Auth-Token'] = token
  }
  return config
})

export const versionApi = {
  // 创建快照
  createSnapshot: (data) => apiClient.post('/api/version/snapshot', data),

  // 获取快照详情
  getSnapshot: (snapshotId) => apiClient.get(`/api/version/snapshot/${snapshotId}`),

  // 获取版本树
  getVersionTree: (sessionId) => apiClient.get(`/api/version/session/${sessionId}/tree`),

  // 列出快照
  listSnapshots: (sessionId, params) => apiClient.get(`/api/version/session/${sessionId}/snapshots`, { params }),

  // 恢复到指定快照
  restoreSnapshot: (sessionId, snapshotId) => apiClient.post(`/api/version/session/${sessionId}/restore/${snapshotId}`),

  // 删除快照
  deleteSnapshot: (snapshotId) => apiClient.delete(`/api/version/snapshot/${snapshotId}`),

  // 创建分支
  createBranch: (sessionId, branchName, fromSnapshot = null) => apiClient.post(`/api/version/session/${sessionId}/branch`, {
    branch_name: branchName,
    from_snapshot: fromSnapshot
  }),

  // 列出分支
  listBranches: (sessionId) => apiClient.get(`/api/version/session/${sessionId}/branches`)
}