import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, ArrowUpRight, BookOpen, Boxes, Building2, Check, CircleAlert, Clock3, RefreshCw, Table2, ReceiptText, Users } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { ordersService } from '../services/orders'
import { productsService, formatPrice } from '../services/products'
import { tablesService } from '../services/tables'
import { venuesService } from '../services/venues'
import { getErrorMessage } from '../services/api'

export default function HomePage() {
  const { user } = useAuth()
  const [data, setData] = useState({ orders: [], products: [], tables: [], venues: [] })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [updated, setUpdated] = useState(null)
  const isAdmin = user.role === 'ADMIN'
  const isCashier = user.role === 'CASHIER'

  async function load() {
    setLoading(true)
    try {
      const [orders, products, tables, venues] = await Promise.all([
        ordersService.list(), productsService.list(), tablesService.list(), venuesService.list(),
      ])
      setData({ orders, products, tables, venues })
      setUpdated(new Date())
      setError('')
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Unable to load the overview.'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [user.id])
  useEffect(() => {
    if (!isCashier) return undefined
    let cancelled = false
    const interval = setInterval(async () => {
      try {
        const orders = await ordersService.list({ background: true })
        if (!cancelled) setData(previous => ({ ...previous, orders }))
      } catch (requestError) {
        if (!cancelled) setError(getErrorMessage(requestError, 'Unable to refresh pending orders.'))
      }
    }, 5000)
    return () => { cancelled = true; clearInterval(interval) }
  }, [isCashier])

  const active = data.orders.filter(order => ['OPEN', 'IN_CASHIER'].includes(order.status))
  const pending = active.filter(order => order.status === 'IN_CASHIER')
  const occupied = data.tables.filter(table => table.status === 'OCCUPIED').length
  const occupancy = data.tables.length ? Math.round(occupied / data.tables.length * 100) : 0
  const rows = (isCashier ? pending : active).slice().sort((a, b) => isCashier
    ? new Date(a.sent_to_cashier_at || a.opened_at) - new Date(b.sent_to_cashier_at || b.opened_at) || a.id - b.id
    : new Date(b.opened_at) - new Date(a.opened_at))
  const metrics = [
    { label: 'Active orders', value: active.length, detail: 'Open and awaiting payment', icon: ReceiptText, color: 'green' },
    { label: 'Occupied tables', value: occupied + ' / ' + data.tables.length, detail: occupancy + '% occupancy', icon: Table2, color: 'blue' },
    { label: 'Pending payment', value: pending.length, detail: formatPrice(pending.reduce((sum, order) => sum + Number(order.total), 0)), icon: Clock3, color: 'amber' },
    { label: 'Active products', value: data.products.length, detail: 'In the shared catalog', icon: BookOpen, color: 'rose' },
  ]

  return (
    <main className="dashboard">
      <header className="page-heading">
        <div><p className="eyebrow">{isAdmin ? 'All venues' : user.venue_name || 'Your venue'}</p><h1>Overview</h1><p className="page-subtitle">Welcome back, {user.full_name.split(' ')[0]}.</p></div>
        <div className="heading-actions">
          <button type="button" className="icon-button refresh-button" onClick={load} disabled={loading} aria-label="Refresh overview" title="Refresh overview"><RefreshCw size={18} className={loading ? 'spin' : ''} /></button>
          <Link className="primary-button" to="/room"><Table2 size={17} /> Open room <ArrowUpRight size={16} /></Link>
        </div>
      </header>

      {error && <div className="error-banner" role="alert"><CircleAlert size={18} /><span>{error}</span><button onClick={load} disabled={loading}>Retry</button></div>}
      <section className="metrics-grid" aria-label="Operational summary" aria-busy={loading}>
        {metrics.map(({ label, value, detail, icon: Icon, color }) => <div className="metric" key={label}>
          <div className="metric-top"><span>{label}</span><span className={'metric-icon ' + color}><Icon size={19} /></span></div>
          <strong className="metric-value">{loading ? <span className="skeleton metric-skeleton" /> : updated ? value : '--'}</strong>
          <span className="metric-detail">{loading ? 'Loading...' : updated ? detail : 'Unavailable'}</span>
        </div>)}
      </section>

      <div className="overview-columns">
        <section className="orders-section">
          <div className="section-heading"><h2>{isCashier ? 'Pending orders' : 'Current orders'} <span className="count-badge">{updated ? rows.length : '--'}</span></h2><Link to="/room" className="text-link">View room <ArrowRight size={15} /></Link></div>
          <div className="data-table-wrap">
            <table><thead><tr><th>Order / Table</th><th>Venue</th><th>Status</th><th className="amount">Total</th><th><span className="sr-only">Open order</span></th></tr></thead>
              <tbody>
                {loading && !updated && <tr><td colSpan={5} className="empty-cell">Loading orders...</td></tr>}
                {!loading && updated && rows.length === 0 && <tr><td colSpan={5}><div className="empty-state"><Check size={24} /><strong>{isCashier ? 'No pending orders' : 'No active orders'}</strong></div></td></tr>}
                {!loading && !updated && <tr><td colSpan={5} className="empty-cell">Overview unavailable.</td></tr>}
                {updated && rows.slice(0, 8).map(order => <tr key={order.id}>
                  <td><Link to={'/orders/' + order.id} className="order-link">#{order.id}<span>{order.table_identifier}</span><span className="mobile-order-venue">{order.venue_name}</span></Link></td>
                  <td>{order.venue_name}</td>
                  <td><span className={'status-pill ' + (order.status === 'IN_CASHIER' ? 'amber' : 'green')}>{order.status === 'IN_CASHIER' ? 'Pending payment' : 'Open'}</span></td>
                  <td className="amount">{formatPrice(order.total)}</td>
                  <td><Link to={'/orders/' + order.id} className="icon-button" aria-label={'View order ' + order.id} title="View order"><ArrowUpRight size={17} /></Link></td>
                </tr>)}
              </tbody>
            </table>
          </div>
          <p className="table-note">{updated ? 'Updated ' + updated.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }) : 'Waiting for data'}{rows.length > 8 ? ' · Showing 8 of ' + rows.length + ' orders' : ''}</p>
        </section>
        <section className="venue-section">
          <div className="section-heading"><h2>{isAdmin ? 'Venues' : 'Your venue'}</h2><Building2 size={18} /></div>
          {updated && data.venues.filter(venue => isAdmin || venue.id === user.venue).map(venue => {
            const tables = data.tables.filter(table => table.venue === venue.id)
            const busy = tables.filter(table => table.status === 'OCCUPIED').length
            return <div className="venue-summary" key={venue.id}>
              <div><strong>{venue.name}</strong><span>{busy} / {tables.length} occupied</span></div>
              <div className="occupancy-track" role="meter" aria-label={venue.name + ' occupancy'} aria-valuenow={busy} aria-valuemin={0} aria-valuemax={Math.max(tables.length, 1)}><span style={{ width: (tables.length ? busy / tables.length * 100 : 0) + '%' }} /></div>
              <small>{tables.length - busy} free tables</small>
            </div>
          })}
          {loading && !updated && <p className="table-note">Loading venues...</p>}
          <div className="section-heading quick-heading"><h2>Quick access</h2></div>
          {user.role !== 'WAITER' && <Link className="quick-link" to="/cashier/pending"><ReceiptText size={18} /><span>Pending orders</span><ArrowRight size={16} /></Link>}
          <Link className="quick-link" to="/catalog"><BookOpen size={18} /><span>Product catalog</span><ArrowRight size={16} /></Link>
          {user.role !== 'WAITER' && <Link className="quick-link" to="/inventory"><Boxes size={18} /><span>Inventory</span><ArrowRight size={16} /></Link>}
          {isAdmin && <Link className="quick-link" to="/admin/users"><Users size={18} /><span>Team members</span><ArrowRight size={16} /></Link>}
        </section>
      </div>
    </main>
  )
}
