import { api } from './index'

export const announcementsApi = {
  list: () => api.get('/announcements/'),
  create: (content) => api.post('/announcements/', { content }),
  revoke: (id) => api.delete(`/announcements/${id}`),
}
