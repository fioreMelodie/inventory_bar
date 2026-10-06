import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { getErrorMessage } from '../services/api'
import { ordersService } from '../services/orders'
import { formatPrice } from '../services/products'
import { venuesService } from '../services/venues'

/**
 * HU22 - Consultar pedidos activos (Cajero).
 *
 * Panel de pedidos pendientes de cobro, en orden de llegada. Se refresca solo
 * para que los pedidos que el mesero envía aparezcan sin recargar.
 */
const REFRESH_INTERVAL_MS = 10000

/** Minutos transcurridos desde que el pedido llegó a caja. */
function waitingMinutes(sentAt) {
  if (!sentAt) return 0
  return Math.max(0, Math.floor((Date.now() - new Date(sentAt).getTime()) / 60000))
}

export default function CashierPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const isAdmin = user.role === 'ADMIN'

  const [orders, setOrders] = useState([])
  const [venues, setVenues] = useState([])
  const [venue, setVenue] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const venueRef = useRef(venue)
  venueRef.current = venue

  useEffect(() => {
    if (isAdmin) loadVenues()
    loadOrders()

    const intervalId = setInterval(loadOrders, REFRESH_INTERVAL_MS)
    return () => clearInterval(intervalId)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (isAdmin) loadOrders()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [venue])

  async function loadVenues() {
    try {
      setVenues(await venuesService.list())
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Unable to load venues.'))
    }
  }

  async function loadOrders() {
    try {
      const data = await ordersService.list({
        status: 'IN_CASHIER',
        venue: isAdmin && venueRef.current ? venueRef.current : undefined,
      })
      setOrders(data)
      setError('')
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Unable to load pending orders.'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="mx-auto max-w-5xl px-4 py-8">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Pending orders</h1>
          <p className="mt-1 text-sm text-slate-500">
            Orders sent by the waiters, in arrival order. The list refreshes on its own.
          </p>
        </div>

        {isAdmin && venues.length > 0 && (
          <div className="w-full sm:w-56">
            <label htmlFor="venue" className="block text-xs font-medium text-slate-600">
              Venue
            </label>
            <select
              id="venue"
              value={venue}
              onChange={(event) => setVenue(event.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            >
              <option value="">All venues</option>
              {venues.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
          </div>
        )}
      </header>

      {error && (
        <p role="alert" className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      {loading && <p className="mt-6 text-sm text-slate-500">Loading pending orders…</p>}

      {!loading && orders.length === 0 && (
        <p className="mt-6 rounded-xl border border-slate-200 bg-white p-6 text-center text-sm text-slate-500">
          No orders waiting to be charged.
        </p>
      )}

      <ul className="mt-6 space-y-3">
        {orders.map((order) => {
          const waiting = waitingMinutes(order.sent_to_cashier_at)

          return (
            <li
              key={order.id}
              className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
            >
              <div className="min-w-0">
                <p className="text-sm font-semibold text-slate-900">
                  Order #{order.id} · {order.table_identifier}
                </p>
                <p className="mt-0.5 text-xs text-slate-500">
                  {order.waiter_name}
                  {isAdmin ? ' · ' + order.venue_name : ''} · sent{' '}
                  {waiting === 0 ? 'just now' : waiting + ' min ago'}
                </p>
              </div>

              <div className="flex items-center gap-4">
                <p className="text-base font-semibold text-slate-900">
                  {formatPrice(order.total)}
                </p>
                <button
                  type="button"
                  onClick={() => navigate('/orders/' + order.id)}
                  className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
                >
                  Charge
                </button>
              </div>
            </li>
          )
        })}
      </ul>
    </main>
  )
}
