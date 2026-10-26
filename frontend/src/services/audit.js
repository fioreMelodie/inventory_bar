import api from './api'

export const auditService = {
  async list(params) {
    const { data } = await api.get('/audit/events/', { params })
    return data
  },
  async detail(id) {
    const { data } = await api.get('/audit/events/' + id + '/')
    return data
  },
}
