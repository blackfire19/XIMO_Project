import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '@/api'

export const useAuthStore = defineStore('auth', () => {
  // token 由后端通过 httpOnly Cookie 管理，前端不持有
  const user = ref(JSON.parse(sessionStorage.getItem('user') || 'null'))

  async function login(username, password) {
    const form = new URLSearchParams()
    form.append('username', username)
    form.append('password', password)
    const res = await api.post('/auth/login', form)
    user.value = res.data.user
    sessionStorage.setItem('user', JSON.stringify(user.value))
  }

  async function logout() {
    try {
      await api.post('/auth/logout')
    } catch (_) {
      // ignore
    }
    user.value = null
    sessionStorage.removeItem('user')
    const { default: router } = await import('@/router')
    router.push({ name: 'Login' })
  }

  async function fetchMe() {
    try {
      const res = await api.get('/auth/me')
      user.value = res.data
      sessionStorage.setItem('user', JSON.stringify(user.value))
    } catch (_) {
      user.value = null
      sessionStorage.removeItem('user')
    }
  }

  function hasRole(...roles) {
    return user.value && roles.includes(user.value.role)
  }

  return { user, login, logout, fetchMe, hasRole }
})
