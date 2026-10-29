import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { ChevronLeft, ChevronRight, Download, Printer, RotateCcw, Search } from 'lucide-react'
import { reportsService } from '../services/reports'
import { venuesService } from '../services/venues'
import { formatPrice, productsService } from '../services/products'
import { getErrorMessage } from '../services/api'
import { useAuth } from '../context/AuthContext'

const fields = ['start_date', 'end_date', 'venue', 'product', 'category']
const money = value => value == null ? 'Not recorded' : formatPrice(value)
const dateLabel = value => new Date(value).toLocaleString('en-US', { timeZone: 'America/Bogota' })

function SalesTable({ rows, showCosts = true }) {
  return <div className="data-table-wrap"><table className="sales-table">
    <thead><tr><th>{showCosts ? 'Date / Receipt' : 'Date'}</th>{showCosts && <th>Venue</th>}<th>Product</th><th>Qty</th>{showCosts && <th className="amount">Purchase value</th>}<th className="amount">Sales</th>{showCosts && <th className="amount">Profit</th>}</tr></thead>
    <tbody>{rows.map(row => <tr key={row.id}>
      <td><time dateTime={row.issued_at}>{dateLabel(row.issued_at)}</time>{showCosts && <span className="sales-secondary">{row.number}</span>}</td>
      {showCosts && <td data-label="Venue">{row.venue_name}</td>}<td data-label="Product"><strong>{row.product_name}</strong><span className="sales-secondary">#{row.product_id}{showCosts && <> · {row.category || 'Not recorded'}</>}</span></td>
      <td data-label="Qty">{row.quantity}</td>{showCosts && <td data-label="Purchase value" className="amount">{money(row.purchase_value)}</td>}
      <td data-label="Sales" className="amount">{money(row.sale_value)}</td>{showCosts && <td data-label="Profit" className="amount">{money(row.profit)}</td>}
    </tr>)}</tbody>
  </table></div>
}

export default function SalesReportPage() {
  const { user } = useAuth()
  const isAdmin = user.role === 'ADMIN'
  const availableFields = isAdmin ? fields : ['start_date', 'end_date', 'product']
  const [params, setParams] = useSearchParams()
  const query = params.toString()
  const applied = Object.fromEntries(availableFields.filter(key => params.get(key)).map(key => [key, params.get(key)]))
  const [draft, setDraft] = useState(applied)
  const [venues, setVenues] = useState([])
  const [catalogCategories, setCatalogCategories] = useState([])
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [venueError, setVenueError] = useState('')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState('')
  const [refresh, setRefresh] = useState(0)
  const [printData, setPrintData] = useState(null)
  const page = Math.max(1, Number(params.get('page')) || 1)

  useEffect(() => { setDraft(applied) }, [query])
  useEffect(() => {
    if (!isAdmin) return undefined
    let cancelled = false
    Promise.all([venuesService.list({ includeInactive: true }), productsService.list({ includeInactive: true })]).then(([list, products]) => {
      if (!cancelled) {
        setVenues(list)
        setCatalogCategories([...new Set(products.map(product => product.category))].sort())
        setVenueError('')
      }
    }).catch(err => { if (!cancelled) setVenueError(getErrorMessage(err, 'Unable to load report filters.')) })
    return () => { cancelled = true }
  }, [refresh, isAdmin])
  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')
    setData(null)
    if (!applied.start_date || !applied.end_date) {
      setLoading(false)
      if (applied.start_date || applied.end_date) setError('Both start and end dates are required.')
      return () => { cancelled = true }
    }
    const load = isAdmin ? reportsService.sales : reportsService.ownSales
    load({ ...applied, page }).then(result => {
      if (!cancelled) setData(result)
    }).catch(err => {
      if (!cancelled) {
        const fields = err?.response?.data
        const dateError = fields?.start_date?.[0] || fields?.end_date?.[0]
        setError(dateError || getErrorMessage(err, 'Unable to generate the sales report.'))
      }
    })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [query, refresh, isAdmin])
  useEffect(() => {
    if (!printData) return undefined
    const finish = () => { setPrintData(null); setBusy('') }
    window.addEventListener('afterprint', finish)
    const timer = setTimeout(() => {
      try { window.print() } catch { finish() }
    }, 0)
    return () => { clearTimeout(timer); window.removeEventListener('afterprint', finish) }
  }, [printData])

  function submit(event) {
    event.preventDefault()
    if (!draft.start_date || !draft.end_date) {
      setError('Both start and end dates are required.')
      return
    }
    if (draft.start_date && draft.end_date && draft.start_date > draft.end_date) {
      setError('End date must be on or after start date.')
      return
    }
    setParams(Object.fromEntries(availableFields.filter(key => draft[key]?.trim()).map(key => [key, draft[key].trim()])))
    setRefresh(value => value + 1)
  }
  async function output(kind) {
    if (busy) return
    setBusy(kind)
    setError('')
    try {
      if (kind === 'csv') await reportsService.exportSales(applied)
      else {
        setPrintData(await reportsService.sales({ ...applied, export: 'print' }))
        return
      }
    } catch (err) { setError(getErrorMessage(err, 'Unable to export the report.')) }
    setBusy('')
  }
  const summary = data?.summary
  const categories = [...new Set([...catalogCategories, ...(data?.categories || []), ...(draft.category && draft.category !== '__unrecorded__' ? [draft.category] : [])])].sort()

  return <main className="sales-report-page">
    <div className="sales-screen">
      <header className="page-heading"><div><p className="eyebrow">Reports</p><h1>Sales report</h1><p className="page-subtitle">{isAdmin ? venues.find(venue => String(venue.id) === applied.venue)?.name || 'All venues' : user.venue_name} · COP</p></div>
        {isAdmin && <div className="heading-actions"><button className="icon-button refresh-button" disabled={!data?.count || Boolean(busy) || loading} onClick={() => output('csv')} aria-label="Export CSV" title="Export CSV"><Download size={18} /></button>
          <button className="icon-button refresh-button" disabled={!data?.count || Boolean(busy) || loading} onClick={() => output('print')} aria-label="Print report" title="Print report"><Printer size={18} /></button></div>}</header>
      <form className="sales-filters" aria-label="Sales filters" onSubmit={submit}>
        <div><label htmlFor="sales-start">From date</label><input id="sales-start" type="date" required value={draft.start_date || ''} onChange={event => setDraft({ ...draft, start_date: event.target.value })} /></div>
        <div><label htmlFor="sales-end">Through date</label><input id="sales-end" type="date" required value={draft.end_date || ''} onChange={event => setDraft({ ...draft, end_date: event.target.value })} /></div>
        <div><label htmlFor="sales-venue">Venue</label>{isAdmin ? <select id="sales-venue" value={draft.venue || ''} onChange={event => setDraft({ ...draft, venue: event.target.value })}><option value="">All venues</option>{venues.map(venue => <option key={venue.id} value={venue.id}>{venue.name}</option>)}</select> : <select id="sales-venue" disabled value={String(user.venue || '')}><option value={String(user.venue || '')}>{user.venue_name || 'No venue assigned'}</option></select>}</div>
        <div><label htmlFor="sales-product">Product ID or name</label><input id="sales-product" type="search" maxLength={150} value={draft.product || ''} onChange={event => setDraft({ ...draft, product: event.target.value })} /></div>
        {isAdmin && <div><label htmlFor="sales-category">Category</label><select id="sales-category" value={draft.category || ''} onChange={event => setDraft({ ...draft, category: event.target.value })}><option value="">All categories</option>{categories.map(category => <option key={category} value={category}>{category}</option>)}<option value="__unrecorded__">Not recorded</option></select></div>}
        <div className="receipt-filter-actions"><button className="primary-button" type="submit" disabled={loading || Boolean(busy)}><Search size={16} /> Generate report</button><button className="icon-button refresh-button" type="button" title="Clear filters" aria-label="Clear filters" disabled={loading || Boolean(busy)} onClick={() => { setParams({}); setDraft({}); setRefresh(value => value + 1) }}><RotateCcw size={18} /></button></div>
      </form>
      {(error || venueError) && <div className="error-banner" role="alert"><span>{error || venueError}</span><button onClick={() => setRefresh(value => value + 1)} disabled={loading}>Retry</button></div>}
      {loading && <p className="empty-cell">Generating report...</p>}
      {/*
        Estado inicial: sin rango de fechas no hay reporte que mostrar. Antes
        la pantalla quedaba vacía bajo el formulario, sin indicar qué hacer.
      */}
      {!loading && !summary && !error && !venueError && <div className="empty-state">
        <strong>Select a date range and generate the report.</strong>
        <span>Results cover paid orders only, with no limit on how far back they go.</span>
      </div>}
      {summary && <>
        <section className={'sales-metrics' + (isAdmin ? '' : ' cashier-sales-metrics')} aria-label="Sales totals">{(isAdmin ? [['Sales', money(summary.sales)], ['Purchase value', money(summary.purchase_value)], ['Profit', money(summary.profit)], ['Units sold', summary.quantity]] : [['Sales', money(summary.sales)], ['Units sold', summary.quantity]]).map(([label, value]) => <div key={label}><span>{label}</span><strong>{value}</strong></div>)}</section>
        {isAdmin && summary.missing_cost_lines > 0 && <p className="sales-warning" role="status">Historical purchase cost is missing for {summary.missing_cost_lines} lines. Total purchase value and profit are not available.</p>}
        <section aria-label="Sales results">{data.count ? <SalesTable rows={data.results} showCosts={isAdmin} /> : <div className="empty-state"><strong>No records found for the selected filters.</strong></div>}</section>
        <footer className="receipts-pagination"><p className="table-note">{summary.transactions} transactions · {data.count} lines · Page {page}</p><div>
          <button className="icon-button" title="Previous page" aria-label="Previous page" disabled={!data.previous || Boolean(busy)} onClick={() => setParams({ ...applied, page: String(page - 1) })}><ChevronLeft size={18} /></button>
          <button className="icon-button" title="Next page" aria-label="Next page" disabled={!data.next || Boolean(busy)} onClick={() => setParams({ ...applied, page: String(page + 1) })}><ChevronRight size={18} /></button></div></footer>
      </>}
    </div>
    {printData && <section className="sales-print" aria-label="Printable sales report"><h1>Sales report</h1><p>Cafe Colombia Bar · COP · America/Bogota</p><p>{applied.start_date || 'Beginning'} to {applied.end_date || 'Present'} · {applied.venue ? venues.find(venue => String(venue.id) === applied.venue)?.name || applied.venue : 'All venues'}</p>
      <p>Product: {applied.product || 'All'} · Category: {applied.category || 'All'}</p>
      <p>Sales: {money(printData.summary.sales)} · Purchase value: {money(printData.summary.purchase_value)} · Profit: {money(printData.summary.profit)}</p>
      {printData.summary.missing_cost_lines > 0 && <p>Historical purchase cost is missing for {printData.summary.missing_cost_lines} lines.</p>}
      <SalesTable rows={printData.results} /></section>}
  </main>
}
