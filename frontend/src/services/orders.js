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

  /**
   * Agrega un producto al pedido y descuenta el stock (HU20).
   * Devuelve el pedido completo con el total ya recalculado.
   */
  async addItem(orderId, productId, quantity) {
    const { data } = await api.post(`/orders/${orderId}/items/`, {
      product: productId,
      quantity,
    })
    return data
  },

  /** Cancela un pedido abierto y reintegra el stock (HU16). */
  async cancel(orderId) {
    const { data } = await api.post(`/orders/${orderId}/cancel/`, {})
    return data
  },
}
