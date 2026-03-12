import axios from 'axios'

const baseURL = import.meta.env.VITE_API_URL || ''
const apiClient = axios.create({
  baseURL: baseURL,
  timeout: 30000,
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

export const dialogueApi = {
  // 获取当前用户会话列表（按活跃时间）
  listSessions: () => apiClient.get('/api/dialogue/sessions'),
  // 创建新会话
  createSession: (data) => apiClient.post('/api/dialogue/session', data),
  // 获取会话历史
  getHistory: (sessionId) => apiClient.get(`/api/dialogue/history/${sessionId}`),
  // 发送消息
  sendMessage: (data) => apiClient.post('/api/dialogue/process', data),
  // 清空会话历史
  clearHistory: (sessionId) => apiClient.delete(`/api/dialogue/history/${sessionId}`),
  // 获取会话状态
  getSessionStatus: (sessionId) => apiClient.get(`/api/dialogue/session/${sessionId}/status`),
  // 重置会话
  resetSession: (sessionId) => apiClient.post(`/api/dialogue/session/${sessionId}/reset`),
  // 获取探索报告
  getReport: (sessionId) => apiClient.get(`/api/dialogue/report/${sessionId}`),
  // 获取叙事文本
  getNarrative: (sessionId) => apiClient.get(`/api/dialogue/narrative/${sessionId}`),
  // 获取记忆球数据
  getMemoryOrbs: (sessionId) => apiClient.get(`/api/dialogue/memory-orbs/${sessionId}`),
}
