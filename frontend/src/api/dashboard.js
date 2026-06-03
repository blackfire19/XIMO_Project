import { api } from './index'

export const dashboardApi = {
  boss: () => api.get('/dashboard/boss'),
  salesperson: () => api.get('/dashboard/salesperson'),
}
