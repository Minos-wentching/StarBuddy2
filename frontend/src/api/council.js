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

export const councilApi = {
  // 获取议会历史
  getHistory: (sessionId, limit = 10, offset = 0) =>
    apiClient.get(`/api/council/session/${sessionId}/history`, {
      params: { limit, offset }
    }),

  // 获取议会详情
  getCouncil: (councilId) => apiClient.get(`/api/council/${councilId}`),

  // 获取活跃议会
  getActiveCouncil: (sessionId) => apiClient.get(`/api/council/session/${sessionId}/active`),

  // 启动议会
  startCouncil: (data) => apiClient.post('/api/council/start', data),

  // 取消议会
  cancelCouncil: (councilId) => apiClient.post(`/api/council/${councilId}/cancel`),

  // 继续议会
  continueCouncil: (councilId) => apiClient.post(`/api/council/${councilId}/continue`),

  // 获取议会进度
  getProgress: (councilId) => apiClient.get(`/api/council/${councilId}/progress`)
}