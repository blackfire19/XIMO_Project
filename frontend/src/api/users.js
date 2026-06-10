import { api } from './index'

export const usersApi = {
  list: () => api.get('/users/'),
  salespersons: () => api.get('/users/salespersons'),
  roles: () => api.get('/users/roles'),
  create: (data) => api.post('/users/', data),
  update: (id, data) => api.put(`/users/${id}`, data),
  toggleActive: (id) => api.put(`/users/${id}/toggle-active`),
}
