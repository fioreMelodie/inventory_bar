import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Clock3, Table2 } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { getErrorMessage } from '../services/api'
import { ordersService } from '../services/orders'
import { tablesService } from '../services/tables'
import { venuesService } from '../services/venues'

/**
 * HU18 - Consultar vista de sala (estado de mesas).
 * HU19 - El Mesero abre un pedido desde una mesa libre.
 *
 * La vista se refresca sola, de modo que los cambios de estado aparecen sin
 * recargar la página.
 */
const REFRESH_INTERVAL_MS = 10000

/** Expresa en texto el tiempo que lleva ocupada una mesa. */
function formatElapsed(minutes) {
  if (minutes === null || minutes === undefined) return ''
  if (minutes < 1) return 'just opened'
  if (minutes < 60) return minutes + ' min'

  const hours = Math.floor(minutes / 60)
  const rest = minutes % 60
  return rest === 0 ? hours + ' h' : hours + ' h ' + rest + ' min'
}

export default function RoomPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const isAdmin = user.role === 'ADMIN'
  const canTakeOrders = user.role === 'WAITER' || isAdmin

  const [venues, setVenues] = useState([])
  const [venue, setVenue] = useState('')
  const [venueName, setVenueName] = useState('')
  const [tables, setTables] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [opening, setOpening] = useState(null)

  // Se guarda en una referencia para que el temporizador siempre consulte la
  // sede seleccionada en ese momento.
  const venueRef = useRef(venue)
  venueRef.current = venue

  useEffect(() => {
    if (isAdmin) loadVenues()
    loadRoom()

    const intervalId = setInterval(() => loadRoom(true), REFRESH_INTERVAL_MS)
    return () => clearInterval(intervalId)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (isAdmin && venue) loadRoom()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [venue])

  async function loadVenues() {
    try {
      const list = await venuesService.list()
      setVenues(list)
      if (list.length > 0) setVenue(String(list[0].id))
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Unable to load venues.'))
    }
  }

  async function loadRoom(background = false) {
    try {
      const data = await tablesService.room({
        venue: isAdmin && venueRef.current ? venueRef.current : undefined,
        background,
      })
      setTables(data.results)
      setVenueName(data.venue_name)
      setError('')
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Unable to load the room.'))
    } finally {
      setLoading(false)
    }
  }

  async function openOrder(table) {
    setError('')
    setOpening(table.id)
    try {
      const order = await ordersService.open(table.id)
      navigate('/orders/' + order.id)
    } catch (requestError) {
      setError(
        requestError?.response?.data?.table?.[0] ||
          getErrorMessage(requestError, 'Unable to open the order.'),
      )
      await loadRoom()
    } finally {
      setOpening(null)
    }
  }

  return (
    <main className="mx-auto max-w-5xl px-4 py-8">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">
            Room{venueName ? ' - ' + venueName : ''}
          </h1>
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
              {venues.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
          </div>
        )}
      </header>

      {!loading && !error && <div className="room-summary" aria-label="Room summary">
        <span><strong>{tables.length}</strong> Total tables</span>
        <span><strong>{tables.filter(table => table.status === 'FREE').length}</strong> Free</span>
        <span><strong>{tables.filter(table => table.status === 'OCCUPIED').length}</strong> Occupied</span>
        <span><strong>{tables.filter(table => table.active_order_status === 'IN_CASHIER').length}</strong> Pending payment</span>
      </div>}

      {error && (
        <p role="alert" className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      {loading && <p className="mt-6 text-sm text-slate-500">Loading room…</p>}

      {!loading && tables.length === 0 && (
        <p className="mt-6 text-sm text-slate-500">
          This venue has no tables configured yet.
        </p>
      )}

      <ul className="room-grid mt-6 grid gap-4">
        {!loading &&
          tables.map((table) => {
            const isFree = table.status === 'FREE'
            const isPendingPayment = !isFree && table.active_order_status === 'IN_CASHIER'
            return (
              <li
                key={table.id}
                className={
                  'room-tile ' + (isFree ? '' : 'occupied')
                }
              >
                <p className="text-sm font-semibold text-slate-900">{table.identifier}</p>
                <div className="mt-1 flex min-h-6 flex-wrap items-center gap-2">
                  <p className={isFree ? 'text-xs text-emerald-700' : 'text-xs text-amber-800'}>
                    {isFree ? 'Free' : 'Occupied'}
                  </p>
                  {isPendingPayment && (
                    <span className="inline-block max-w-full rounded border border-sky-200 bg-sky-100 px-2 py-0.5 text-xs font-medium text-sky-900">
                      Pending payment
                    </span>
                  )}
                </div>
                <Table2 className="table-symbol" size={46} strokeWidth={1.2} aria-hidden="true" />

                {!isFree && (
                  <p className="mb-3 flex items-center gap-1 text-xs text-slate-600">
                    <Clock3 size={12} />
                    Open for {formatElapsed(table.occupied_minutes)}
                  </p>
                )}

                {canTakeOrders && isFree && (
                  <button
                    type="button"
                    onClick={() => openOrder(table)}
                    disabled={opening === table.id}
                    className="mt-3 w-full rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-brand-700 disabled:bg-slate-300"
                  >
                    {opening === table.id ? 'Opening…' : 'Open order'}
                  </button>
                )}

                {!isFree && table.active_order && (
                  <button
                    type="button"
                    onClick={() => navigate('/orders/' + table.active_order)}
                    className="mt-3 w-full rounded-lg border border-amber-300 px-3 py-1.5 text-xs font-medium text-amber-900 transition hover:bg-amber-100"
                  >
                    View order
                  </button>
                )}
              </li>
            )
          })}
      </ul>
    </main>
  )
}
