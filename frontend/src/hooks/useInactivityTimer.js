import { useEffect, useRef } from 'react'

/**
 * HU02 - Cierre automático de sesión por inactividad.
 *
 * Reinicia el contador ante cualquier interacción del usuario y ejecuta
 * `onTimeout` al cumplirse el tiempo sin interacción.
 *
 * El corte definitivo lo aplica el servidor; este temporizador solo evita que
 * la pantalla quede abierta y notifica el vencimiento a la API.
 */

/** Tiempo de inactividad permitido: 3 minutos. No configurable por el usuario. */
export const INACTIVITY_TIMEOUT_MS = 3 * 60 * 1000

const ACTIVITY_EVENTS = ['click', 'keydown', 'scroll', 'mousemove', 'touchstart']

export default function useInactivityTimer(onTimeout, enabled = true, onActivity) {
  const callbackRef = useRef(onTimeout)
  callbackRef.current = onTimeout
  const activityRef = useRef(onActivity)
  activityRef.current = onActivity

  useEffect(() => {
    if (!enabled) return undefined

    let timerId
    let lastNotification = Date.now()

    const resetTimer = (event) => {
      clearTimeout(timerId)
      timerId = setTimeout(() => callbackRef.current(), INACTIVITY_TIMEOUT_MS)
      if (event && Date.now() - lastNotification >= 30000) {
        lastNotification = Date.now()
        activityRef.current?.()
      }
    }

    ACTIVITY_EVENTS.forEach((eventName) =>
      window.addEventListener(eventName, resetTimer, { passive: true }),
    )
    resetTimer()

    return () => {
      clearTimeout(timerId)
      ACTIVITY_EVENTS.forEach((eventName) =>
        window.removeEventListener(eventName, resetTimer),
      )
    }
  }, [enabled])
}
