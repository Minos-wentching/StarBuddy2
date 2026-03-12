import axios from 'axios'

// 创建axios实例
// 在ModelSpace部署中，前后端同源，使用相对路径
const baseURL = import.meta.env.VITE_API_URL || ''
const apiClient = axios.create({
  baseURL: baseURL,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器：添加token（使用自定义头部避免与ModelSpace冲突）
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      // 使用自定义头部，避免使用ModelSpace占用的Authorization头部
      config.headers['X-Auth-Token'] = token
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器：处理token过期
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      try {
        const refreshToken = localStorage.getItem('refresh_token')
        if (refreshToken) {
          const response = await axios.post(
            '/api/auth/refresh',
            { refresh_token: refreshToken }
          )
          const { access_token, refresh_token } = response.data
          localStorage.setItem('access_token', access_token)
          if (refresh_token) {
            localStorage.setItem('refresh_token', refresh_token)
          }
          originalRequest.headers['X-Auth-Token'] = access_token
          return apiClient(originalRequest)
        }
      } catch (refreshError) {
        console.error('刷新令牌失败:', refreshError)
        // 清除本地存储，跳转到登录页
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        localStorage.removeItem('user')
        localStorage.removeItem('current_session_id')
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

// API方法
export const authApi = {
  // 注册
  register: (data) => apiClient.post('/api/auth/register', data),

  // 登录
  login: (data) => apiClient.post('/api/auth/login', data),

  // 快速登录（仅用户名）
  quickLogin: (username) => apiClient.post('/api/auth/quick-login', { username }),

  // 登出
  logout: () => apiClient.post('/api/auth/logout'),

  // 获取当前用户
  getCurrentUser: () => apiClient.get('/api/auth/me'),

  // 刷新令牌
  refreshToken: (refreshToken) =>
    apiClient.post('/api/auth/refresh', { refresh_token: refreshToken }),

  // 更新用户资料
  updateProfile: (userData) => apiClient.put('/api/auth/me', userData),

  // 首次登录问卷解析
  parseOnboarding: (payload) => apiClient.post('/api/auth/onboarding/parse', payload),

  // 获取人格画像存档
  getOnboardingArchives: () => apiClient.get('/api/auth/onboarding/archives'),

  // 恢复人格画像版本
  restoreOnboardingArchive: (payload) => apiClient.post('/api/auth/onboarding/restore', payload)
}
