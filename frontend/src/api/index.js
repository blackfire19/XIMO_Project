import axios from 'axios'
import { message } from 'ant-design-vue'

export const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

// 请求拦截：自动携带 token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截：统一错误提示
api.interceptors.response.use(
  (res) => res,
  (err) => {
    const status = err.response?.status
    const detail = err.response?.data?.detail

    if (status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      window.location.href = '/login'
      return Promise.reject(err)
    }

    message.error(detail || '请求失败，请稍后重试')
    return Promise.reject(err)
  },
)
