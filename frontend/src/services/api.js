import axios from 'axios'

/**
 * Cliente HTTP único de la aplicación.
 * El token de acceso se adjunta automáticamente en cada petición.
 */
const api = axios.create({
  baseURL: '/api',
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
 * Extrae el mensaje de error de una respuesta de la API.
 * Los mensajes llegan desde el backend ya redactados en inglés.
 */
export function getErrorMessage(error, fallback = 'Something went wrong. Please try again.') {
  return error?.response?.data?.detail || fallback
}

export default api
