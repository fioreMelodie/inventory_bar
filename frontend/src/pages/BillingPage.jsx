import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { getErrorMessage } from '../services/api'
import { billingService } from '../services/billing'
import { formatPrice } from '../services/products'
import { venuesService } from '../services/venues'

const EMPTY_FILTERS = { dateFrom: '', dateTo: '', number: '', venue: '' }

/**
 * HU26 - Consultar historial de facturas.
 *
 * Los filtros se aplican en el servidor y son combinables. El historial es de
 * solo consulta: no hay forma de editar ni anular una factura.
 */
export default function BillingPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const isAdmin = user.role === 'ADMIN'

  const [invoices, setInvoices] = useState([])
  const [venues, setVenues] = useState([])
  const [filters, setFilters] = useState(EMPTY_FILTERS)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (isAdmin) loadVenues()
    loadInvoices()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function loadVenues() {
    try {
      setVenues(await venuesService.list())
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Unable to load venues.'))
    }
  }

  async function loadInvoices(applied = filters) {
    setLoading(true)
    setError('')
    try {
      setInvoices(await billingService.list(applied))
    } catch (requestError) {
      setInvoices([])
      setError(getErrorMessage(requestError, 'Unable to load the invoice history.'))
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

    loadInvoices()
  }

  function clearFilters() {
    setFilters(EMPTY_FILTERS)
    loadInvoices(EMPTY_FILTERS)
  }

  return (
    <main className="mx-auto max-w-5xl px-4 py-8">
      <header>
        <h1 className="text-xl font-semibold text-slate-900">Invoices</h1>
        <p className="mt-1 text-sm text-slate-500">
          {isAdmin
            ? 'Complete history for every venue, since the system went live.'
            : 'Complete history for your venue, since the system went live.'}
        </p>
      </header>

      <form
        onSubmit={handleSubmit}
        className="mt-6 rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
      >
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
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
            <label htmlFor="number" className="block text-xs font-medium text-slate-600">
              Invoice number
            </label>
            <input
              id="number"
              type="search"
              value={filters.number}
              onChange={(event) => setFilters({ ...filters, number: event.target.value })}
              placeholder="F-01-000001"
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            />
          </div>

          {isAdmin && (
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
          )}
        </div>

        {error && (
          <p role="alert" className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}

        <div className="mt-4 flex justify-end gap-2">
          <button
            type="button"
            onClick={clearFilters}
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
                  Invoice
                </th>
                <th scope="col" className="px-4 py-3 font-medium">
                  Date
                </th>
                {isAdmin && (
                  <th scope="col" className="px-4 py-3 font-medium">
                    Venue
                  </th>
                )}
                <th scope="col" className="px-4 py-3 font-medium">
                  Table
                </th>
                <th scope="col" className="px-4 py-3 font-medium">
                  Payment
                </th>
                <th scope="col" className="px-4 py-3 text-right font-medium">
                  Total
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading && (
                <tr>
                  <td colSpan={isAdmin ? 6 : 5} className="px-4 py-6 text-center text-slate-500">
                    Loading invoices…
                  </td>
                </tr>
              )}

              {!loading && invoices.length === 0 && (
                <tr>
                  <td colSpan={isAdmin ? 6 : 5} className="px-4 py-6 text-center text-slate-500">
                    No invoices match the selected filters.
                  </td>
                </tr>
              )}

              {!loading &&
                invoices.map((invoice) => (
                  <tr
                    key={invoice.id}
                    onClick={() => navigate('/billing/invoices/' + invoice.id)}
                    className="cursor-pointer transition hover:bg-slate-50"
                  >
                    <td className="px-4 py-3 font-medium text-slate-900">{invoice.number}</td>
                    <td className="px-4 py-3 text-slate-600">
                      {new Date(invoice.created_at).toLocaleString('en-US')}
                    </td>
                    {isAdmin && (
                      <td className="px-4 py-3 text-slate-600">{invoice.venue_name}</td>
                    )}
                    <td className="px-4 py-3 text-slate-600">{invoice.table_identifier}</td>
                    <td className="px-4 py-3 text-slate-600">
                      {invoice.payment_method_label}
                    </td>
                    <td className="px-4 py-3 text-right font-medium text-slate-900">
                      {formatPrice(invoice.total)}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  )
}
