import { useEffect, useState } from 'react'
import api from '../services/api'

/**
 * HU03 - Manejo de pérdida de conexión.
 *
 * Criterio de aceptación: la pérdida de conexión debe detectarse en un máximo
 * de 5 segundos. Se combinan dos mecanismos:
 *   1. Los eventos `online` / `offline` del navegador, que son inmediatos.
 *   2. Un sondeo al endpoint de salud cada 5 segundos, que además detecta la
 *      caída del servidor aunque el equipo siga conectado a la red local.
 */
export const CONNECTION_CHECK_INTERVAL_MS = 5000

export default function useConnectionStatus() {
  const [isOnline, setIsOnline] = useState(() => navigator.onLine)

  useEffect(() => {
    let cancelled = false

    const goOffline = () => setIsOnline(false)
    const goOnline = () => setIsOnline(true)

    const checkConnection = async () => {
      if (!navigator.onLine) {
        if (!cancelled) setIsOnline(false)
        return
      }
      try {
        await api.get('/health/', { timeout: CONNECTION_CHECK_INTERVAL_MS / 2 })
        if (!cancelled) setIsOnline(true)
      } catch (error) {
        // Solo se considera desconexión si no hubo respuesta del servidor.
        // Un error HTTP significa que la conexión sigue disponible.
        if (!cancelled && !error.response) setIsOnline(false)
      }
    }

    window.addEventListener('offline', goOffline)
    window.addEventListener('online', goOnline)
    checkConnection()
    const intervalId = setInterval(checkConnection, CONNECTION_CHECK_INTERVAL_MS / 2)

    return () => {
      cancelled = true
      clearInterval(intervalId)
      window.removeEventListener('offline', goOffline)
      window.removeEventListener('online', goOnline)
    }
  }, [])

  return isOnline
}
