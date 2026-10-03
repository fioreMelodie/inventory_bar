import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
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

    const intervalId = setInterval(loadRoom, REFRESH_INTERVAL_MS)
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

  async function loadRoom() {
    try {
      const data = await tablesService.room({
        venue: isAdmin && venueRef.current ? venueRef.current : undefined,
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
          <p className="mt-1 text-sm text-slate-500">
            {canTakeOrders
              ? 'Pick a free table to open a new order. The view refreshes on its own.'
              : 'Current status of the tables. The view refreshes on its own.'}
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

      {loading && <p className="mt-6 text-sm text-slate-500">Loading room…</p>}

      {!loading && tables.length === 0 && (
        <p className="mt-6 text-sm text-slate-500">
          This venue has no tables configured yet.
        </p>
      )}

      <ul className="mt-6 grid gap-3 sm:grid-cols-3 lg:grid-cols-4">
        {!loading &&
          tables.map((table) => {
            const isFree = table.status === 'FREE'
            return (
              <li
                key={table.id}
                className={
                  isFree
                    ? 'rounded-xl border border-emerald-200 bg-emerald-50 p-4'
                    : 'rounded-xl border border-amber-200 bg-amber-50 p-4'
                }
              >
                <p className="text-sm font-semibold text-slate-900">{table.identifier}</p>
                <p
                  className={
                    isFree ? 'mt-1 text-xs text-emerald-700' : 'mt-1 text-xs text-amber-800'
                  }
                >
                  {isFree ? 'Free' : 'Occupied'}
                </p>

                {!isFree && (
                  <p className="mt-1 text-xs text-slate-600">
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
