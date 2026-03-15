import axios from 'axios'

const baseURL = import.meta.env.VITE_API_URL || ''

const apiClient = axios.create({
  baseURL,
  headers: { 'Content-Type': 'application/json' }
})

apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) config.headers['X-Auth-Token'] = token
    return config
  },
  (error) => Promise.reject(error)
)

export const patientApi = {
  getProfile: () => apiClient.get('/api/me/patient-profile'),
  updateProfile: (payload) => apiClient.put('/api/me/patient-profile', payload),
  getSettings: () => apiClient.get('/api/me/patient-settings'),
  updateSettings: (payload) => apiClient.put('/api/me/patient-settings', payload),
  getMetrics: () => apiClient.get('/api/me/patient-metrics'),
  incrementBlackClick: () => apiClient.post('/api/me/patient-metrics/black-click'),
  resetBlackClick: () => apiClient.post('/api/me/patient-metrics/black-click/reset')
}
