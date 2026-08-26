import { Navigate } from 'react-router-dom'
import useInactivityTimer from '../hooks/useInactivityTimer'
import { HOME_ROUTE_BY_ROLE, useAuth } from '../context/AuthContext'

/**
 * Restringe el acceso a las rutas privadas.
 * Si se indica `roles`, además verifica que el rol del usuario esté permitido.
 * La verificación definitiva se hace siempre en el servidor.
 */
export default function ProtectedRoute({ children, roles }) {
  const { user, isAuthenticated, expireSessionByInactivity } = useAuth()

  // HU02 - Cierre automático tras 3 minutos sin interacción.
  useInactivityTimer(expireSessionByInactivity, isAuthenticated)

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  if (roles && !roles.includes(user.role)) {
    return <Navigate to={HOME_ROUTE_BY_ROLE[user.role] || '/login'} replace />
  }

  return children
}
