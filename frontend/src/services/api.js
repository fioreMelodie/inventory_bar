import axios from 'axios'

/**
 * Cliente HTTP único de la aplicación.
 * El token de acceso se adjunta automáticamente en cada petición.
 */
const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
})

export const TOKEN_KEY = 'bar_inventory_access'
export const REFRESH_KEY = 'bar_inventory_refresh'
export const USER_KEY = 'bar_inventory_user'

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

/**
 * Aviso de que la sesión dejó de ser válida.
 * AuthContext lo registra para limpiar el estado y volver al login.
 */
let onSessionExpired = () => {}

export function setSessionExpiredHandler(handler) {
  onSessionExpired = handler
}

/** Rutas que no deben intentar renovarse: son las que gestionan la sesión. */
const SESSION_ENDPOINTS = ['/auth/login/', '/auth/refresh/', '/auth/logout/', '/auth/session/']

function isSessionEndpoint(url = '') {
  return SESSION_ENDPOINTS.some((endpoint) => url.includes(endpoint))
}

// Si varias peticiones fallan a la vez, todas esperan la misma renovación en
// lugar de pedir una cada una, lo que invalidaría los refresh tokens entre sí.
let refreshInFlight = null

async function refreshAccessToken(background = false) {
  const refresh = localStorage.getItem(REFRESH_KEY)
  if (!refresh) throw new Error('No refresh token available')

  // Instancia aparte para que esta petición no pase por el interceptor y
  // provoque una recursión infinita.
  const { data } = await axios.post('/api/auth/refresh/', { refresh }, {
    timeout: 10000,
    headers: background ? { 'X-Session-Activity': 'background' } : undefined,
  })

  if (localStorage.getItem(REFRESH_KEY) !== refresh) {
    throw new Error('Session changed while refreshing')
  }

  localStorage.setItem(TOKEN_KEY, data.access)
  if (data.refresh) localStorage.setItem(REFRESH_KEY, data.refresh)

  return data.access
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config

    const shouldRetry =
      error.response?.status === 401 &&
      original &&
      !original._retried &&
      !isSessionEndpoint(original.url)

    if (!shouldRetry) {
      return Promise.reject(error)
    }

    original._retried = true

    try {
      refreshInFlight = refreshInFlight ?? refreshAccessToken(
        original.headers?.['X-Session-Activity'] === 'background',
      )
      const token = await refreshInFlight

      original.headers.Authorization = `Bearer ${token}`
      return api(original)
    } catch (refreshError) {
      // La sesión ya no es recuperable: se cerró, venció por inactividad o la
      // cuenta fue inactivada.
      onSessionExpired(refreshError?.response?.data?.detail)
      return Promise.reject(error)
    } finally {
      refreshInFlight = null
    }
  },
)

/**
 * Extrae el mensaje de error de una respuesta de la API.
 * Los mensajes llegan desde el backend ya redactados en inglés.
 */
export function getErrorMessage(error, fallback = 'Something went wrong. Please try again.') {
  return error?.response?.data?.detail || fallback
}

/** Completa los listados paginados sin perder registros despues de la pagina 1. */
export async function listAll(url, config = {}) {
  const results = []
  let page = 1
  let next
  do {
    const { data } = await api.get(url, {
      ...config, params: { ...config.params, page },
    })
    if (Array.isArray(data)) return data
    results.push(...data.results)
    next = data.next
    page += 1
  } while (next)
  return results
}

export default api
