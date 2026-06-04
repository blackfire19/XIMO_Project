import { api } from './index'

export const pricingSheetsApi = {
  list: (params = {}) => api.get('/pricing-sheets/', { params }),
  get: (id) => api.get(`/pricing-sheets/${id}`),
  create: (data) => api.post('/pricing-sheets/', data),
  update: (id, data) => api.put(`/pricing-sheets/${id}`, data),
  confirm: (id) => api.patch(`/pricing-sheets/${id}/confirm`),
  convertToPI: (id) => api.post(`/pricing-sheets/${id}/convert-to-pi`),

  uploadImage: (id, category, file) => {
    const form = new FormData()
    form.append('file', file)
    return api.post(`/pricing-sheets/${id}/images/${category}`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  deleteImage: (id, imageId) => api.delete(`/pricing-sheets/${id}/images/${imageId}`),
}
