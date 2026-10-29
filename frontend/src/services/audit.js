import api from './api'

/** Módulo 11 - Auditoría y Trazabilidad. */
export const auditService = {
  /** Log de eventos con filtros combinables (HU30). */
  async list({ dateFrom, dateTo, username, eventType, venue } = {}) {
    const params = {}
    if (dateFrom) params.date_from = dateFrom
    if (dateTo) params.date_to = dateTo
    if (username) params.username = username.trim()
    if (eventType) params.event_type = eventType
    if (venue) params.venue = venue

    const { data } = await api.get('/audit/events/', { params })
    return data.results ?? data
  },

  /** Tipos de evento disponibles, para poblar el filtro. */
  async eventTypes() {
    const { data } = await api.get('/audit/events/event-types/')
    return data
  },
}
