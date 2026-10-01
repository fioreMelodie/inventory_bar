import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import api, {
  REFRESH_KEY,
  TOKEN_KEY,
  USER_KEY,
  setSessionExpiredHandler,
} from '../services/api'

const AuthContext = createContext(null)

/** Ruta principal de cada rol tras iniciar sesión (HU01). */
export const HOME_ROUTE_BY_ROLE = {
  ADMIN: '/admin',
  CASHIER: '/cashier',
  WAITER: '/waiter',
}

/** Etiquetas de rol mostradas en la interfaz (en inglés). */
export const ROLE_LABELS = {
  ADMIN: 'Administrator',
  CASHIER: 'Cashier',
  WAITER: 'Waiter',
}

function readStoredUser() {
  try {
    const raw = localStorage.getItem(USER_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

/** Avisos que se muestran en la pantalla de inicio de sesión. */
export const SESSION_NOTICES = {
  INACTIVITY: 'Your session was closed after 3 minutes of inactivity. Please sign in again.',
  DISCONNECTION: 'Your session was closed because the connection was lost. Your data is safe.',
  EXPIRED: 'Your session is no longer valid. Please sign in again.',
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(readStoredUser)
  const [sessionNotice, setSessionNotice] = useState('')

  const login = useCallback(async (username, password) => {
    setSessionNotice('')
    const { data } = await api.post('/auth/login/', { username, password })
    localStorage.setItem(TOKEN_KEY, data.access)
    localStorage.setItem(REFRESH_KEY, data.refresh)
    localStorage.setItem(USER_KEY, JSON.stringify(data.user))
    setUser(data.user)
    return data.user
  }, [])

  const clearSession = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(REFRESH_KEY)
    localStorage.removeItem(USER_KEY)
    setUser(null)
  }, [])

  // Cuando la API no logra renovar el token, la sesión deja de ser
  // recuperable: se limpia el estado local y se vuelve al formulario de
  // inicio de sesión con el motivo correspondiente.
  useEffect(() => {
    setSessionExpiredHandler((detail) => {
      clearSession()
      setSessionNotice(detail || SESSION_NOTICES.EXPIRED)
    })
  }, [clearSession])

  /**
   * HU02 - El temporizador de inactividad venció: se notifica al servidor para
   * que invalide la sesión y se limpia el estado local.
   */
  const expireSessionByInactivity = useCallback(async () => {
    const refresh = localStorage.getItem(REFRESH_KEY)
    if (refresh) {
      try {
        await api.post('/auth/session/expire/', { refresh })
      } catch {
        // Si la API no responde, la sesión igualmente se cierra en el
        // navegador y el token quedará invalidado al vencer.
      }
    }
    clearSession()
    setSessionNotice(SESSION_NOTICES.INACTIVITY)
  }, [clearSession])

  /**
   * Cierra la sesión en el servidor indicando el motivo, para que quede
   * correctamente diferenciado en el log de auditoría (HU03).
   */
  const closeSession = useCallback(
    async (reason) => {
      const refresh = localStorage.getItem(REFRESH_KEY)
      if (refresh) {
        try {
          await api.post('/auth/logout/', { refresh, reason })
        } catch {
          // Sin conexión no es posible notificar al servidor; la sesión se
          // cierra localmente y el token quedará invalidado al vencer.
        }
      }
      clearSession()
    },
    [clearSession],
  )

  /** HU03 - El usuario pulsó "Sign out". */
  const signOut = useCallback(async () => {
    await closeSession('MANUAL')
    setSessionNotice('')
  }, [closeSession])

  /** HU03 - El usuario confirmó el aviso de pérdida de conexión. */
  const reportConnectionLoss = useCallback(async () => {
    await closeSession('DISCONNECTION')
    setSessionNotice(SESSION_NOTICES.DISCONNECTION)
  }, [closeSession])

  const value = useMemo(
    () => ({
      user,
      isAuthenticated: Boolean(user),
      login,
      clearSession,
      expireSessionByInactivity,
      signOut,
      reportConnectionLoss,
      sessionNotice,
      setSessionNotice,
    }),
    [
      user,
      login,
      clearSession,
      expireSessionByInactivity,
      signOut,
      reportConnectionLoss,
      sessionNotice,
    ],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
