import api from './api'

/** Módulo 8 - Gestión de Pedidos. */
export const ordersService = {
  /** Lista los pedidos de la sede, opcionalmente filtrados por estado. */
  async list({ venue, status, table } = {}) {
    const params = {}
    if (venue) params.venue = venue
    if (status) params.status = status
    if (table) params.table = table

    const { data } = await api.get('/orders/', { params })
    return data.results ?? data
  },

  /** Consulta un pedido concreto. */
  async retrieve(id) {
    const { data } = await api.get(`/orders/${id}/`)
    return data
  },

  /** Abre un pedido sobre una mesa libre (HU19). */
  async open(tableId) {
    const { data } = await api.post('/orders/', { table: tableId })
    return data
  },
}
