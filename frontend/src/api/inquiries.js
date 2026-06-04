import { api } from './index'

export const inquiriesApi = {
  list: (params = {}) => api.get('/inquiries/', { params }),
  get: (id) => api.get(`/inquiries/${id}`),
  create: (data) => api.post('/inquiries/', data),
  update: (id, data) => api.put(`/inquiries/${id}`, data),
  setDeposit: (id, data) => api.patch(`/inquiries/${id}/deposit`, data),
  void: (id) => api.patch(`/inquiries/${id}/void`),

  uploadFile: (id, docType, file, note) => {
    const form = new FormData()
    form.append('doc_type', docType)
    form.append('file', file)
    if (note) form.append('note', note)
    return api.post(`/inquiries/${id}/files`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  deleteFile: (id, fileId) => api.delete(`/inquiries/${id}/files/${fileId}`),
}

export const formalOrdersApi = {
  list: (params = {}) => api.get('/formal-orders/', { params }),
  get: (id) => api.get(`/formal-orders/${id}`),
  convert: (data) => api.post('/formal-orders/', data),
  update: (id, data) => api.put(`/formal-orders/${id}`, data),
  setStatus: (id, status) => api.patch(`/formal-orders/${id}/status`, { status }),

  uploadFile: (id, docType, file) => {
    const form = new FormData()
    form.append('doc_type', docType)
    form.append('file', file)
    return api.post(`/formal-orders/${id}/files`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  deleteFile: (id, fileId) => api.delete(`/formal-orders/${id}/files/${fileId}`),

  addBL: (id, data) => api.post(`/formal-orders/${id}/bls`, data),
  updateBL: (id, blId, data) => api.put(`/formal-orders/${id}/bls/${blId}`, data),
  deleteBL: (id, blId) => api.delete(`/formal-orders/${id}/bls/${blId}`),
}
