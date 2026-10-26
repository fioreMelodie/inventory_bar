import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { ArrowUpRight, ChevronLeft, ChevronRight, CircleAlert, ReceiptText, RefreshCw, RotateCcw, Search } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { getErrorMessage } from '../services/api'
import { paymentsService } from '../services/payments'
import { formatPrice } from '../services/products'
import { venuesService } from '../services/venues'

const METHODS = { CASH: 'Cash', CREDIT_CARD: 'Credit card', DEBIT_CARD: 'Debit card' }

export default function InvoicesPage() {
  const { user } = useAuth()
  const isAdmin = user.role === 'ADMIN'
  const [params, setParams] = useSearchParams()
  const venue = isAdmin ? params.get('venue') || '' : ''
  const startDate = params.get('start_date') || ''
  const endDate = params.get('end_date') || ''
  const number = params.get('number') || ''
  const filtered = Boolean(venue || startDate || endDate || number)
  const [draft, setDraft] = useState({ startDate, endDate, number })
  const [filterError, setFilterError] = useState('')
  const rawPage = Number(params.get('page') || 1)
  const page = Number.isSafeInteger(rawPage) && rawPage > 0 ? rawPage : 1
  const [venues, setVenues] = useState([])
  const [venueError, setVenueError] = useState('')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [refresh, setRefresh] = useState(0)

  useEffect(() => {
    setDraft({ startDate, endDate, number })
    setFilterError('')
  }, [startDate, endDate, number])

  useEffect(() => {
    if (!isAdmin) return undefined
    let cancelled = false
    venuesService.list({ includeInactive: true }).then(list => {
      if (!cancelled) { setVenues(list); setVenueError('') }
    }).catch(err => { if (!cancelled) setVenueError(getErrorMessage(err, 'Unable to load venues.')) })
    return () => { cancelled = true }
  }, [isAdmin, refresh])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')
    setData(null)
    paymentsService.receipts({ page, ...appliedFilters() }).then(result => {
      if (!cancelled) setData(result)
    }).catch(err => {
      if (!cancelled) setError(getErrorMessage(err, 'Unable to load receipts.'))
    }).finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [page, venue, startDate, endDate, number, refresh])

  function appliedFilters() {
    return { ...(venue ? { venue } : {}), ...(startDate ? { start_date: startDate } : {}),
      ...(endDate ? { end_date: endDate } : {}), ...(number ? { number } : {}) }
  }

  function changePage(next) {
    setParams({ ...appliedFilters(), ...(next > 1 ? { page: String(next) } : {}) })
  }

  function editFilter(field, value) {
    setDraft(current => ({ ...current, [field]: value }))
    setFilterError('')
  }

  function applyFilters(event) {
    event.preventDefault()
    if (draft.startDate && draft.endDate && draft.startDate > draft.endDate) {
      setFilterError('End date must be on or after start date.')
      return
    }
    setFilterError('')
    setParams({ ...(venue ? { venue } : {}), ...(draft.startDate ? { start_date: draft.startDate } : {}),
      ...(draft.endDate ? { end_date: draft.endDate } : {}), ...(draft.number.trim() ? { number: draft.number.trim() } : {}) })
  }

  function clearFilters() {
    setDraft({ startDate: '', endDate: '', number: '' })
    setFilterError('')
    setParams({})
  }

  return <main className="invoices-page">
    <header className="page-heading">
      <div><p className="eyebrow">Cashier</p><h1>Receipts</h1><p className="page-subtitle">{isAdmin ? venues.find(item => String(item.id) === venue)?.name || 'All venues' : user.venue_name}</p></div>
      <div className="heading-actions">
        {isAdmin && <div><label htmlFor="receipts-venue" className="block text-xs text-slate-500">Venue</label>
          <select id="receipts-venue" className="mt-1 border px-3 py-2 text-sm" value={venue} onChange={event => {
            const next = appliedFilters()
            delete next.venue
            setParams({ ...next, ...(event.target.value ? { venue: event.target.value } : {}) })
          }}>
            <option value="">All venues</option>{venues.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select></div>}
        <button className="icon-button refresh-button" onClick={() => setRefresh(value => value + 1)} disabled={loading} title="Refresh receipts" aria-label="Refresh receipts"><RefreshCw size={18} className={loading ? 'spin' : ''} /></button>
      </div>
    </header>
    <form className="receipt-filters" aria-label="Receipt filters" onSubmit={applyFilters}>
      <div><label htmlFor="receipt-start">From date</label><input id="receipt-start" type="date" value={draft.startDate} onChange={event => editFilter('startDate', event.target.value)} /></div>
      <div><label htmlFor="receipt-end">Through date</label><input id="receipt-end" type="date" value={draft.endDate} aria-invalid={Boolean(filterError)} aria-describedby={filterError ? 'receipt-filter-error' : undefined} onChange={event => editFilter('endDate', event.target.value)} /></div>
      <div className="receipt-number-filter"><label htmlFor="receipt-number-filter">Receipt number</label><input id="receipt-number-filter" type="search" maxLength={60} value={draft.number} onChange={event => editFilter('number', event.target.value)} /></div>
      <div className="receipt-filter-actions"><button className="primary-button" type="submit"><Search size={16} /> Apply filters</button>
        <button className="icon-button refresh-button" type="button" title="Clear filters" aria-label="Clear filters" onClick={clearFilters} disabled={!filtered && !draft.startDate && !draft.endDate && !draft.number}><RotateCcw size={18} /></button></div>
    </form>
    {filterError && <p id="receipt-filter-error" className="error-banner" role="alert">{filterError}</p>}
    {(error || venueError) && <div className="error-banner" role="alert"><CircleAlert size={18} /><span>{error || venueError}</span><button onClick={() => setRefresh(value => value + 1)} disabled={loading}>Retry</button></div>}
    <section className="receipts-section" aria-label="Issued receipts" aria-busy={loading}>
      {loading && <p className="empty-cell">Loading receipts...</p>}
      {!loading && error && <div className="empty-state"><strong>Receipts unavailable</strong>{page > 1 && <button className="text-link" onClick={() => changePage(1)}>Back to first page</button>}</div>}
      {!loading && data?.count === 0 && <div className="empty-state"><ReceiptText size={26} /><strong>{filtered ? 'No matching receipts' : 'No receipts yet'}</strong>{filtered && <button className="text-link" onClick={clearFilters}>Clear filters</button>}</div>}
      {!loading && data?.results.length > 0 && <div className="data-table-wrap"><table className="receipts-table">
        <thead><tr><th>Receipt / Table</th><th>Issued</th><th>Venue</th><th>Method</th><th className="amount">Total</th><th><span className="sr-only">Receipt details</span></th></tr></thead>
        <tbody>{data.results.map(invoice => <tr key={invoice.id}>
          <td><Link className="order-link" to={'/invoices/' + invoice.id} state={{ from: '/invoices', search: '?' + params.toString() }}>{invoice.number}<span>{invoice.table_identifier}</span></Link></td>
          <td data-label="Issued"><time dateTime={invoice.issued_at}>{new Date(invoice.issued_at).toLocaleString('en-US', { timeZone: 'America/Bogota' })}</time></td>
          <td data-label="Venue">{invoice.venue_name}</td>
          <td data-label="Method">{METHODS[invoice.method] || invoice.method}</td>
          <td data-label="Total" className="amount">{formatPrice(invoice.total)}</td>
          <td><Link className="text-link" to={'/invoices/' + invoice.id} state={{ from: '/invoices', search: '?' + params.toString() }} aria-label={'View receipt ' + invoice.number}>View receipt <ArrowUpRight size={16} /></Link></td>
        </tr>)}</tbody>
      </table></div>}
    </section>
    {data && data.count > 0 && <footer className="receipts-pagination">
      <p className="table-note" aria-live="polite">{data.count} receipts · Page {page}</p>
      <div><button className="icon-button" disabled={!data.previous || loading} onClick={() => changePage(page - 1)} title="Previous page" aria-label="Previous page"><ChevronLeft size={18} /></button>
        <button className="icon-button" disabled={!data.next || loading} onClick={() => changePage(page + 1)} title="Next page" aria-label="Next page"><ChevronRight size={18} /></button></div>
    </footer>}
  </main>
}
