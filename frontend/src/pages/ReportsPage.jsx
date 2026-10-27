import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { getErrorMessage } from '../services/api'
import { formatPrice, productsService } from '../services/products'
import { reportsService } from '../services/reports'
import { venuesService } from '../services/venues'

/** Fecha de hoy en el formato que espera un input date. */
function today() {
  return new Date().toISOString().slice(0, 10)
}

/** Primer día del mes en curso. */
function startOfMonth() {
  const date = new Date()
  date.setDate(1)
  return date.toISOString().slice(0, 10)
}

/**
 * HU27 - Reporte de ventas del Administrador (todas las sedes).
 * HU28 - Reporte de ventas del Cajero (sede propia).
 * HU29 - Combinación de filtros sobre el reporte.
 */
export default function ReportsPage() {
  const { user } = useAuth()
  const isAdmin = user.role === 'ADMIN'

  const [filters, setFilters] = useState({
    dateFrom: startOfMonth(),
    dateTo: today(),
    venue: '',
    product: '',
    category: '',
  })

  const [venues, setVenues] = useState([])
  const [products, setProducts] = useState([])
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    loadOptions()
    generate()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function loadOptions() {
    try {
      const requests = [productsService.list({ includeInactive: isAdmin })]
      if (isAdmin) requests.push(venuesService.list())

      const [productList, venueList] = await Promise.all(requests)
      setProducts(productList)
      if (venueList) setVenues(venueList)
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Unable to load the filters.'))
    }
  }

  async function generate(event) {
    if (event) event.preventDefault()
    setError('')

    if (!filters.dateFrom || !filters.dateTo) {
      setError('Select a start date and an end date.')
      return
    }

    if (filters.dateFrom > filters.dateTo) {
      setError('The start date cannot be later than the end date.')
      return
    }

    setLoading(true)
    try {
      setReport(await reportsService.sales(filters))
    } catch (requestError) {
      setReport(null)
      setError(getErrorMessage(requestError, 'Unable to generate the report.'))
    } finally {
      setLoading(false)
    }
  }

  const categories = [...new Set(products.map((product) => product.category))].sort()
  const rows = report?.results ?? []

  return (
    <main className="mx-auto max-w-6xl px-4 py-8">
      <header>
        <h1 className="text-xl font-semibold text-slate-900">Sales report</h1>
        <p className="mt-1 text-sm text-slate-500">
          {isAdmin
            ? 'Paid orders across every venue, with cost and profit.'
            : 'Paid orders in your venue.'}
        </p>
      </header>

      <form
        onSubmit={generate}
        className="mt-6 rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
      >
        <p className="mb-4 text-xs text-slate-500">
          The date range is required. Every other filter is optional and they combine:
          each one narrows the results further.
        </p>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <div>
            <label htmlFor="date-from" className="block text-xs font-medium text-slate-600">
              From <span className="text-red-500">*</span>
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
              To <span className="text-red-500">*</span>
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
            <label htmlFor="venue" className="block text-xs font-medium text-slate-600">
              Venue
            </label>
            {isAdmin ? (
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
            ) : (
              <input
                id="venue"
                type="text"
                value={user.venue_name ?? 'Your venue'}
                disabled
                className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-500"
              />
            )}
          </div>

          <div>
            <label htmlFor="product" className="block text-xs font-medium text-slate-600">
              Product
            </label>
            <select
              id="product"
              value={filters.product}
              onChange={(event) => setFilters({ ...filters, product: event.target.value })}
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            >
              <option value="">All products</option>
              {products.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="category" className="block text-xs font-medium text-slate-600">
              Category
            </label>
            <select
              id="category"
              value={filters.category}
              onChange={(event) => setFilters({ ...filters, category: event.target.value })}
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            >
              <option value="">All categories</option>
              {categories.map((item) => (
                <option key={item} value={item}>
                  {item}
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
            onClick={() => window.print()}
            disabled={rows.length === 0}
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:opacity-40"
          >
            Print
          </button>
          <button
            type="submit"
            disabled={loading}
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-brand-700 disabled:bg-slate-300"
          >
            {loading ? 'Generating…' : 'Generate report'}
          </button>
        </div>
      </form>

      {report && rows.length > 0 && (
        <section className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <SummaryTile label="Units sold" value={report.summary.quantity} />
          <SummaryTile label="Sales" value={formatPrice(report.summary.sale_value)} />
          {isAdmin && (
            <SummaryTile label="Cost" value={formatPrice(report.summary.purchase_value)} />
          )}
          {isAdmin && (
            <SummaryTile label="Profit" value={formatPrice(report.summary.profit)} highlight />
          )}
        </section>
      )}

      <section className="mt-6 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th scope="col" className="px-4 py-3 font-medium">
                  Date
                </th>
                {isAdmin && (
                  <th scope="col" className="px-4 py-3 font-medium">
                    Venue
                  </th>
                )}
                <th scope="col" className="px-4 py-3 font-medium">
                  Product
                </th>
                <th scope="col" className="px-4 py-3 text-right font-medium">
                  Qty
                </th>
                {isAdmin && (
                  <th scope="col" className="px-4 py-3 text-right font-medium">
                    Cost
                  </th>
                )}
                <th scope="col" className="px-4 py-3 text-right font-medium">
                  Sales
                </th>
                {isAdmin && (
                  <th scope="col" className="px-4 py-3 text-right font-medium">
                    Profit
                  </th>
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading && (
                <tr>
                  <td colSpan={isAdmin ? 7 : 4} className="px-4 py-6 text-center text-slate-500">
                    Generating report…
                  </td>
                </tr>
              )}

              {!loading && rows.length === 0 && (
                <tr>
                  <td colSpan={isAdmin ? 7 : 4} className="px-4 py-6 text-center text-slate-500">
                    No records found for the selected filters.
                  </td>
                </tr>
              )}

              {!loading &&
                rows.map((row) => (
                  <tr key={row.date + '-' + row.venue + '-' + row.product}>
                    <td className="px-4 py-3 text-slate-600">{row.date}</td>
                    {isAdmin && (
                      <td className="px-4 py-3 text-slate-600">{row.venue_name}</td>
                    )}
                    <td className="px-4 py-3 font-medium text-slate-900">
                      {row.product_name}
                    </td>
                    <td className="px-4 py-3 text-right text-slate-600">{row.quantity}</td>
                    {isAdmin && (
                      <td className="px-4 py-3 text-right text-slate-600">
                        {formatPrice(row.purchase_value)}
                      </td>
                    )}
                    <td className="px-4 py-3 text-right text-slate-900">
                      {formatPrice(row.sale_value)}
                    </td>
                    {isAdmin && (
                      <td className="px-4 py-3 text-right font-medium text-emerald-700">
                        {formatPrice(row.profit)}
                      </td>
                    )}
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  )
}

function SummaryTile({ label, value, highlight = false }) {
  return (
    <div
      className={
        highlight
          ? 'rounded-xl border border-emerald-200 bg-emerald-50 p-4'
          : 'rounded-xl border border-slate-200 bg-white p-4'
      }
    >
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p
        className={
          highlight
            ? 'mt-1 text-xl font-semibold text-emerald-800'
            : 'mt-1 text-xl font-semibold text-slate-900'
        }
      >
        {value}
      </p>
    </div>
  )
}
