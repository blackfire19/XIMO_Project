import { api } from './index'

export const orderApi = {
  list: (params) => api.get('/orders/', { params }),
  get: (id) => api.get(`/orders/${id}`),
  updateStatus: (id, data) => api.patch(`/orders/${id}/status`, data),

  // 出运
  listShipments: (orderId) => api.get(`/orders/${orderId}/shipments`),
  addShipment: (orderId, data) => api.post(`/orders/${orderId}/shipments`, data),
  updateShipment: (orderId, shipmentId, data) => api.put(`/orders/${orderId}/shipments/${shipmentId}`, data),
  deleteShipment: (orderId, shipmentId) => api.delete(`/orders/${orderId}/shipments/${shipmentId}`),

  // 附件
  listAttachments: (orderId) => api.get(`/orders/${orderId}/attachments`),
  uploadAttachment: (orderId, formData) => api.post(`/orders/${orderId}/attachments`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
  deleteAttachment: (orderId, attachmentId) => api.delete(`/orders/${orderId}/attachments/${attachmentId}`),
}
