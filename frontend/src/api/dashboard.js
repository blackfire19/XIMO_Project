import { api } from './index'

export const dashboardApi = {
  boss: () => api.get('/dashboard/boss'),
  salesperson: () => api.get('/dashboard/salesperson'),
  finance: () => api.get('/dashboard/finance'),
  logistics: () => api.get('/dashboard/logistics'),
  worldMap: () => api.get('/dashboard/world-map'),
}
