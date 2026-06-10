import axios from 'axios'
import { message } from 'ant-design-vue'

export const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
  withCredentials: true, // 携带 httpOnly Cookie，token 不再存于 localStorage
})

// 响应拦截：统一错误提示
api.interceptors.response.use(
  (res) => res,
  (err) => {
    const status = err.response?.status
    const detail = err.response?.data?.detail

    if (status === 401) {
      window.location.href = '/login'
      return Promise.reject(err)
    }

    message.error(detail || '请求失败，请稍后重试')
    return Promise.reject(err)
  },
)
