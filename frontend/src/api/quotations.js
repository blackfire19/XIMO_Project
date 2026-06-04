import { api } from './index'

export const quotationsApi = {
  list: (params = {}) => api.get('/quotations/', { params }),
  get: (id) => api.get(`/quotations/${id}`),
  create: (data) => api.post('/quotations/', data),
  update: (id, data) => api.put(`/quotations/${id}`, data),
  updateStatus: (id, status) => api.patch(`/quotations/${id}/status`, null, { params: { status } }),
  convertToOrder: (id) => api.post(`/quotations/${id}/convert-to-order`),
}
