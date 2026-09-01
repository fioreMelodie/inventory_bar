import api from './api'

/** Módulo 3 - Administración de Usuarios. */
export const usersService = {
  /** Lista las cuentas de usuario. */
  async list({ includeInactive = false } = {}) {
    const { data } = await api.get('/users/', {
      params: includeInactive ? { include_inactive: 'true' } : undefined,
    })
    return data.results ?? data
  },

  /** Crea una cuenta con rol y sede asignada (HU06). */
  async create(user) {
    const { data } = await api.post('/users/', user)
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
