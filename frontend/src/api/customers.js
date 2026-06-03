import { api } from './index'

export const customersApi = {
  list: (params = {}) => api.get('/customers/', { params }),
  get: (id) => api.get(`/customers/${id}`),
  create: (data) => api.post('/customers/', data),
  update: (id, data) => api.put(`/customers/${id}`, data),
  upgradeFreq: (id, freq) => api.put(`/customers/${id}/upgrade-freq`, { freq }),

  listFollowUps: (id, page = 1, pageSize = 5) =>
    api.get(`/customers/${id}/follow-ups`, { params: { page, page_size: pageSize } }),
  createFollowUp: (id, formData) =>
    api.post(`/customers/${id}/follow-ups`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  listAllFollowUps: (params = {}) => {
    // 将布尔值转为后端能识别的字符串（axios 默认会序列化 bool，保留原样即可）
    return api.get('/customers/follow-ups/all', { params })
  },
}
