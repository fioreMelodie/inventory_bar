import api from './api'

/** Módulo 10 - Reportes. */
export const reportsService = {
  /**
   * Reporte de ventas (HU27 / HU28).
   * El rango de fechas es obligatorio; los demás filtros son opcionales.
   */
  async sales({ dateFrom, dateTo, venue, product, category } = {}) {
    const params = { date_from: dateFrom, date_to: dateTo }
    if (venue) params.venue = venue
    if (product) params.product = product
    if (category) params.category = category

    const { data } = await api.get('/reports/sales/', { params })
    return data
  },
}
