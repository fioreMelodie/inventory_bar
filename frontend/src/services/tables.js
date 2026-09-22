import api from './api'

/** Módulo 7 - Gestión de Mesas. */
export const tablesService = {
  /** Lista las mesas. Cajero y Mesero reciben siempre las de su sede. */
  async list({ venue, includeInactive = false } = {}) {
    const params = {}
    if (venue) params.venue = venue
    if (includeInactive) params.include_inactive = 'true'

    const { data } = await api.get('/tables/', { params })
    return data.results ?? data
  },

  /** Crea una mesa en una sede (HU17). */
  async create({ venue, identifier }) {
    const { data } = await api.post('/tables/', { venue, identifier })
    return data
  },

  /** Edita el identificador de una mesa sin pedidos activos (HU17). */
  async update(id, { identifier }) {
    const { data } = await api.patch(`/tables/${id}/`, { identifier })
    return data
  },

  /** Inactiva una mesa. Las mesas no se eliminan (HU17). */
  async deactivate(id) {
    const { data } = await api.post(`/tables/${id}/deactivate/`, {})
    return data
  },
}
