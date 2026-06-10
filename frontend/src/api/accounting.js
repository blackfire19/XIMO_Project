import { api } from './index'

const _noThrow = { validateStatus: s => s < 500 }

export const accountingApi = {
  get: (orderId) => api.get(`/accounting/${orderId}`, _noThrow),
  save: (orderId, formData) => api.post(`/accounting/${orderId}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    ..._noThrow,
  }),
  toggleSalary: (orderId) => api.patch(`/accounting/${orderId}/salary`, null, _noThrow),
  deleteFile: (orderId) => api.delete(`/accounting/${orderId}/file`, _noThrow),
}
