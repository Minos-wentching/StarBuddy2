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

export const imageApi = {
  // 获取会话的疗愈图片列表
  getImages: (sessionId) => apiClient.get(`/api/images/${sessionId}`),

  // 获取单条日记详情
  getDiary: (diaryId) => apiClient.get(`/api/images/diary/${diaryId}`),

  // 添加日记反馈
  addFeedback: (data) => apiClient.post('/api/images/diary/feedback', data)
}
