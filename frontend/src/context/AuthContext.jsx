import { createContext, useCallback, useContext, useMemo, useState } from 'react'
import api, { REFRESH_KEY, TOKEN_KEY, USER_KEY } from '../services/api'

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

export function AuthProvider({ children }) {
  const [user, setUser] = useState(readStoredUser)

  const login = useCallback(async (username, password) => {
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

  const value = useMemo(
    () => ({ user, isAuthenticated: Boolean(user), login, clearSession }),
    [user, login, clearSession],
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
