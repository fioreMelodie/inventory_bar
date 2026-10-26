import api from './api'

export const reportsService = {
  async ownSales(params) {
    const { data } = await api.get('/reports/sales/own/', { params })
    return data
  },
  async sales(params) {
    const { data } = await api.get('/reports/sales/', { params })
    return data
  },
  async exportSales(params) {
    const { data } = await api.get('/reports/sales/', { params: { ...params, export: 'csv' }, responseType: 'blob' })
    const url = URL.createObjectURL(data)
    const link = document.createElement('a')
    link.href = url
    link.download = 'sales-report.csv'
    link.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  },
}
