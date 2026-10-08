import api, { listAll } from './api'

/** Módulo 3 - Administración de Usuarios. */
export const usersService = {
  /** Lista las cuentas de usuario. */
  async list({ includeInactive = false } = {}) {
    return listAll('/users/', {
      params: includeInactive ? { include_inactive: 'true' } : undefined,
    })
  },

  /** Crea una cuenta con rol y sede asignada (HU06). */
  async create(user) {
    const { data } = await api.post('/users/', user)
    return data
  },

  /** Actualiza una cuenta existente (HU07). */
  async update(id, user) {
    const { data } = await api.patch(`/users/${id}/`, user)
    return data
  },

  /** Inactiva una cuenta. Requiere confirmacion explicita (HU08). */
  async deactivate(id) {
    const { data } = await api.post(`/users/${id}/deactivate/`, { confirm: true })
    return data
  },

  /** Reactiva una cuenta inactiva (HU08). */
  async activate(id) {
    const { data } = await api.post(`/users/${id}/activate/`, { confirm: true })
    return data
  },
}

/** Etiquetas de rol mostradas en la interfaz. */
export const ROLE_OPTIONS = [
  { value: 'ADMIN', label: 'Administrator' },
  { value: 'CASHIER', label: 'Cashier' },
  { value: 'WAITER', label: 'Waiter' },
]

/** Roles cuyo alcance se limita a una sede y, por tanto, la exigen. */
export const ROLES_REQUIRING_VENUE = ['CASHIER', 'WAITER']
