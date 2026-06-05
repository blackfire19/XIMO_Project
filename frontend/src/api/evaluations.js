import { api } from './index'

export const evaluationsApi = {
  create: (data) => api.post('/evaluations', data),
  list: (params) => api.get('/evaluations', { params }),
  remove: (id) => api.delete(`/evaluations/${id}`),
  stats: (period) => api.get('/evaluations/stats', { params: { period } }),
}
