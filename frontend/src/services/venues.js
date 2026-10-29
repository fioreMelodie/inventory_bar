import api, { listAll } from './api'

/** Módulo 2 - Administración de Sedes. */
export const venuesService = {
  /** Lista las sedes. Con includeInactive se incluyen también las inactivas. */
  async list({ includeInactive = false } = {}) {
    return listAll('/venues/', {
      params: includeInactive ? { include_inactive: 'true' } : undefined,
    })
  },

  /** Crea una sede (HU04). */
  async create(venue) {
    const { data } = await api.post('/venues/', venue)
    return data
  },

  /** Actualiza nombre y dirección de una sede (HU05). */
  async update(id, venue) {
    const { data } = await api.patch(`/venues/${id}/`, venue)
    return data
  },

  /** Inactiva una sede. Requiere confirmación explícita (HU05). */
  async deactivate(id) {
    const { data } = await api.post(`/venues/${id}/deactivate/`, { confirm: true })
    return data
  },
}

/** Extrae el mensaje de error de un campo devuelto por la API. */
export function getFieldError(error, field) {
  const detail = error?.response?.data?.[field]
  return Array.isArray(detail) ? detail[0] : detail
}
