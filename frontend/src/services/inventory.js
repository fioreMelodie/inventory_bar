import api from './api'

/** Módulo 6 - Gestión de Inventario. */
export const inventoryService = {
  /**
   * Registra una entrada de mercancía (HU14).
   * El Cajero omite la sede: el servidor usa la suya.
   */
  async registerEntry({ product, quantity, venue }) {
    const payload = { product, quantity }
    if (venue) payload.venue = venue

    const { data } = await api.post('/inventory/entries/', payload)
    return data
  },

  /**
   * Stock actual de una sede (HU15).
   * El Cajero siempre recibe el de su sede, aunque indique otra.
   */
  async stock({ venue, background = false } = {}) {
    const { data } = await api.get('/inventory/stock/', {
      params: venue ? { venue } : undefined,
      headers: background ? { 'X-Session-Activity': 'background' } : undefined,
    })
    return data
  },
}
