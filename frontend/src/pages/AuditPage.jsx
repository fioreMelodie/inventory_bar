import { useEffect, useState } from 'react'
import { getErrorMessage } from '../services/api'
import { auditService } from '../services/audit'
import { venuesService } from '../services/venues'

const EMPTY_FILTERS = { dateFrom: '', dateTo: '', username: '', eventType: '', venue: '' }

/**
 * HU30 - Consultar el log de eventos del sistema.
 *
 * Acceso exclusivo del Administrador. El log es de solo lectura: no existe
 * ninguna acción que permita alterarlo.
 */
export default function AuditPage() {
  const [events, setEvents] = useState([])
  const [eventTypes, setEventTypes] = useState([])
  const [venues, setVenues] = useState([])
  const [filters, setFilters] = useState(EMPTY_FILTERS)
  const [selected, setSelected] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    loadOptions()
    loadEvents()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function loadOptions() {
    try {
      const [types, venueList] = await Promise.all([
        auditService.eventTypes(),
        venuesService.list(),
      ])
      setEventTypes(types)
      setVenues(venueList)
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Unable to load the filters.'))
    }
  }

  async function loadEvents(applied = filters) {
    setLoading(true)
    setError('')
    try {
      setEvents(await auditService.list(applied))
    } catch (requestError) {
      setEvents([])
      setError(getErrorMessage(requestError, 'Unable to load the event log.'))
    } finally {
      setLoading(false)
    }
  }

  function handleSubmit(event) {
    event.preventDefault()

    if (filters.dateFrom && filters.dateTo && filters.dateFrom > filters.dateTo) {
      setError('The start date cannot be later than the end date.')
      return
    }

    loadEvents()
  }

  return (
    <main className="mx-auto max-w-6xl px-4 py-8">
      <header>
        <h1 className="text-xl font-semibold text-slate-900">Event log</h1>
        <p className="mt-1 text-sm text-slate-500">
          Every relevant action in the system, since it went live. Records cannot be
          changed or deleted by anyone.
        </p>
      </header>

      <form
        onSubmit={handleSubmit}
        className="mt-6 rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
      >
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <div>
            <label htmlFor="date-from" className="block text-xs font-medium text-slate-600">
              From
            </label>
            <input
              id="date-from"
              type="date"
              value={filters.dateFrom}
              onChange={(event) => setFilters({ ...filters, dateFrom: event.target.value })}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            />
          </div>

          <div>
            <label htmlFor="date-to" className="block text-xs font-medium text-slate-600">
              To
            </label>
            <input
              id="date-to"
              type="date"
              value={filters.dateTo}
              onChange={(event) => setFilters({ ...filters, dateTo: event.target.value })}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            />
          </div>

          <div>
            <label htmlFor="username" className="block text-xs font-medium text-slate-600">
              User
            </label>
            <input
              id="username"
              type="search"
              value={filters.username}
              onChange={(event) => setFilters({ ...filters, username: event.target.value })}
              placeholder="Username"
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            />
          </div>

          <div>
            <label htmlFor="event-type" className="block text-xs font-medium text-slate-600">
              Event type
            </label>
            <select
              id="event-type"
              value={filters.eventType}
              onChange={(event) => setFilters({ ...filters, eventType: event.target.value })}
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            >
              <option value="">All events</option>
              {eventTypes.map((type) => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="venue" className="block text-xs font-medium text-slate-600">
              Venue
            </label>
            <select
              id="venue"
              value={filters.venue}
              onChange={(event) => setFilters({ ...filters, venue: event.target.value })}
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
        </div>

        {error && (
          <p role="alert" className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}

        <div className="mt-4 flex justify-end gap-2">
          <button
            type="button"
            onClick={() => {
              setFilters(EMPTY_FILTERS)
              loadEvents(EMPTY_FILTERS)
            }}
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
          >
            Clear
          </button>
          <button
            type="submit"
            disabled={loading}
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-brand-700 disabled:bg-slate-300"
          >
            {loading ? 'Searching…' : 'Search'}
          </button>
        </div>
      </form>

      <section className="mt-6 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th scope="col" className="px-4 py-3 font-medium">
                  Date and time
                </th>
                <th scope="col" className="px-4 py-3 font-medium">
                  User
                </th>
                <th scope="col" className="px-4 py-3 font-medium">
                  Event
                </th>
                <th scope="col" className="px-4 py-3 font-medium">
                  Entity
                </th>
                <th scope="col" className="px-4 py-3 font-medium">
                  Venue
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading && (
                <tr>
                  <td colSpan={5} className="px-4 py-6 text-center text-slate-500">
                    Loading events…
                  </td>
                </tr>
              )}

              {!loading && events.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-6 text-center text-slate-500">
                    No events found for the selected filters.
                  </td>
                </tr>
              )}

              {!loading &&
                events.map((event) => (
                  <tr
                    key={event.id}
                    onClick={() => setSelected(event)}
                    className="cursor-pointer transition hover:bg-slate-50"
                  >
                    <td className="px-4 py-3 text-slate-600">
                      {new Date(event.created_at).toLocaleString('en-US')}
                    </td>
                    <td className="px-4 py-3 font-medium text-slate-900">
                      {event.username}
                    </td>
                    <td className="px-4 py-3 text-slate-600">{event.event_type_label}</td>
                    <td className="px-4 py-3 text-slate-600">
                      {event.entity ? event.entity + ' ' + event.entity_id : '-'}
                    </td>
                    <td className="px-4 py-3 text-slate-600">{event.venue_name || '-'}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </section>

      {selected && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="event-detail-title"
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 px-4"
        >
          <div className="w-full max-w-lg rounded-xl bg-white p-6 shadow-xl">
            <h2 id="event-detail-title" className="text-base font-semibold text-slate-900">
              {selected.event_type_label}
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              {new Date(selected.created_at).toLocaleString('en-US')}
            </p>

            <dl className="mt-4 space-y-2 text-sm">
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">User</dt>
                <dd className="text-right text-slate-900">
                  {selected.user_full_name
                    ? selected.user_full_name + ' (' + selected.username + ')'
                    : selected.username}
                </dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">Venue</dt>
                <dd className="text-right text-slate-900">{selected.venue_name || '-'}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">Entity</dt>
                <dd className="text-right text-slate-900">
                  {selected.entity ? selected.entity + ' ' + selected.entity_id : '-'}
                </dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">IP address</dt>
                <dd className="text-right text-slate-900">{selected.ip_address || '-'}</dd>
              </div>
            </dl>

            <p className="mt-4 rounded-lg bg-slate-50 px-3 py-3 text-sm text-slate-700">
              {selected.description}
            </p>

            <div className="mt-6 flex justify-end">
              <button
                type="button"
                onClick={() => setSelected(null)}
                autoFocus
                className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-brand-700"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  )
}
