import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { getErrorMessage } from '../services/api'
import { ordersService } from '../services/orders'
import { tablesService } from '../services/tables'
import { venuesService } from '../services/venues'

/**
 * HU19 - Crear pedido (Mesero).
 *
 * Vista de sala desde la que el Mesero abre un pedido seleccionando una mesa
 * libre. La vista completa en tiempo real se desarrolla en la HU18.
 */
export default function RoomPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const isAdmin = user.role === 'ADMIN'
  const canTakeOrders = user.role === 'WAITER' || isAdmin

  const [venues, setVenues] = useState([])
  const [venue, setVenue] = useState('')
  const [tables, setTables] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [opening, setOpening] = useState(null)

  useEffect(() => {
    if (isAdmin) loadVenues()
    loadTables()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (isAdmin && venue) loadTables()
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

  async function loadTables() {
    setLoading(true)
    try {
      setTables(await tablesService.list({ venue: isAdmin && venue ? venue : undefined }))
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
      await loadTables()
    } finally {
      setOpening(null)
    }
  }

  return (
    <main className="mx-auto max-w-5xl px-4 py-8">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Room</h1>
          <p className="mt-1 text-sm text-slate-500">
            {canTakeOrders
              ? 'Pick a free table to open a new order.'
              : 'Current status of the tables in your venue.'}
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
              </li>
            )
          })}
      </ul>
    </main>
  )
}
