import api from './api'

export const paymentsService = {
  async receipts(params = {}) {
    const { data } = await api.get('/invoices/', { params })
    return data
  },
  async card(payload) {
    const { data } = await api.post('/payments/card/', payload)
    return data
  },
  async cash(payload) {
    const { data } = await api.post('/payments/cash/', payload)
    return data
  },
  async receipt(id) {
    const { data } = await api.get('/invoices/' + id + '/')
    return data
  },
}
