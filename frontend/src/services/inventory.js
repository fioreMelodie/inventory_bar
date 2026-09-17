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
}
