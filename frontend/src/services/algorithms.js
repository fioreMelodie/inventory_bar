import api from './api'

export const algorithmsService = {
  async overview(params) {
    const { data } = await api.get('/algorithms/overview/', { params })
    return data
  },
  async change(amount) {
    const { data } = await api.get('/algorithms/change/', { params: { amount } })
    return data
  },
}
