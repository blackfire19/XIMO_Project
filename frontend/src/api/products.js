import { api } from './index'

export const productsApi = {
  list: (params = {}) => api.get('/products/', { params }),

  importWarehouse: (warehouse, file) => {
    const form = new FormData()
    form.append('file', file)
    return api.post(`/products/import/${encodeURIComponent(warehouse)}`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
}
