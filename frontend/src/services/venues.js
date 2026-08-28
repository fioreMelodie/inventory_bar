import api from './api'

/** Módulo 2 - Administración de Sedes. */
export const venuesService = {
  /** Lista las sedes. Con includeInactive se incluyen también las inactivas. */
  async list({ includeInactive = false } = {}) {
    const { data } = await api.get('/venues/', {
      params: includeInactive ? { include_inactive: 'true' } : undefined,
    })
    return data.results ?? data
  },

  /** Crea una sede (HU04). */
  async create(venue) {
    const { data } = await api.post('/venues/', venue)
    return data
  },
}

/** Extrae el mensaje de error de un campo devuelto por la API. */
export function getFieldError(error, field) {
  const detail = error?.response?.data?.[field]
  return Array.isArray(detail) ? detail[0] : detail
}
