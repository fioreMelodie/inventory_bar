import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowUpRight, Check, CircleAlert, Clock3, RefreshCw } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { getErrorMessage } from '../services/api'
import { ordersService } from '../services/orders'
import { formatPrice } from '../services/products'
import { venuesService } from '../services/venues'

function waitingTime(sentAt, now) {
  if (!sentAt) return 'Not recorded'
  const minutes = Math.max(0, Math.floor((now - new Date(sentAt).getTime()) / 60000))
  if (minutes < 1) return 'Just received'
  if (minutes < 60) return minutes + ' min'
  return Math.floor(minutes / 60) + ' h ' + minutes % 60 + ' min'
}

export default function PendingOrdersPage() {
  const { user } = useAuth()
  const isAdmin = user.role === 'ADMIN'
  const [venue, setVenue] = useState('')
  const [venues, setVenues] = useState([])
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [venueError, setVenueError] = useState('')
  const [updated, setUpdated] = useState(null)
  const [now, setNow] = useState(Date.now())
  const [refresh, setRefresh] = useState(0)

  useEffect(() => {
    if (!isAdmin) return undefined
    let cancelled = false
    venuesService.list().then(list => {
      if (!cancelled) setVenues(list)
    }).catch(requestError => {
      if (!cancelled) setVenueError(getErrorMessage(requestError, 'Unable to load venues.'))
    })
    return () => { cancelled = true }
  }, [isAdmin])

  useEffect(() => {
    let cancelled = false
    let timer
    setOrders([])
    setUpdated(null)
    setError('')
    setLoading(true)
    async function load(background = false) {
      try {
        const list = await ordersService.pending({ venue: isAdmin ? venue : undefined, background })
        if (!cancelled) {
          setOrders(list)
          setError('')
          setUpdated(new Date())
          setNow(Date.now())
        }
      } catch (requestError) {
        if (!cancelled) setError(getErrorMessage(requestError, 'Unable to load pending orders.'))
      } finally {
        if (!cancelled) {
          setLoading(false)
          timer = setTimeout(() => load(true), 5000)
        }
      }
    }
    load()
    return () => { cancelled = true; clearTimeout(timer) }
  }, [venue, isAdmin, refresh])

  const total = orders.reduce((sum, order) => sum + Number(order.total), 0)
  return (
    <main className="pending-page">
      <header className="page-heading">
        <div><p className="eyebrow">Cashier</p><h1>Pending orders</h1><p className="page-subtitle">{isAdmin ? venues.find(item => String(item.id) === venue)?.name || 'All venues' : user.venue_name}</p></div>
        <div className="heading-actions">
          {isAdmin && <div><label htmlFor="pending-venue" className="block text-xs text-slate-500">Venue</label>
            <select id="pending-venue" className="mt-1 border px-3 py-2 text-sm" value={venue} onChange={event => setVenue(event.target.value)}>
              <option value="">All venues</option>{venues.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}
            </select>
          </div>}
          <button className="icon-button refresh-button" type="button" onClick={() => setRefresh(value => value + 1)} disabled={loading} title="Refresh pending orders" aria-label="Refresh pending orders"><RefreshCw size={18} className={loading ? 'spin' : ''} /></button>
        </div>
      </header>
      {(error || venueError) && <div className="error-banner" role="alert"><CircleAlert size={18} /><span>{error || venueError}</span>{error && <button onClick={() => setRefresh(value => value + 1)} disabled={loading}>Retry</button>}</div>}
      <div className="queue-summary" aria-live="polite">
        <span><strong>{loading || !updated ? '--' : orders.length}</strong> Pending orders</span>
        <span><strong>{loading || !updated ? '--' : formatPrice(total)}</strong> Awaiting payment</span>
      </div>
      <section aria-label="Payment queue" aria-busy={loading} className="queue-section">
        {loading && <p className="empty-cell">Loading pending orders...</p>}
        {!loading && !updated && <p className="empty-cell">Queue unavailable.</p>}
        {!loading && updated && orders.length === 0 && <div className="empty-state"><Check size={26} /><strong>No pending orders</strong></div>}
        {!loading && orders.length > 0 && <div className="data-table-wrap">
          <table className="queue-table">
            <thead><tr><th>Order / Table</th><th>Venue</th><th>Waiter</th><th>Sent to cashier</th><th>Waiting</th><th className="amount">Total</th><th><span className="sr-only">Order details</span></th></tr></thead>
            <tbody>{orders.map(order => <tr key={order.id}>
              <td><Link className="order-link" to={'/orders/' + order.id} state={{ from: '/cashier/pending' }}>#{order.id}<span>{order.table_identifier}</span></Link></td>
              <td data-label="Venue">{order.venue_name}</td>
              <td data-label="Waiter">{order.waiter_name}</td>
              <td data-label="Sent to cashier">{order.sent_to_cashier_at ? <time dateTime={order.sent_to_cashier_at}>{new Date(order.sent_to_cashier_at).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</time> : 'Not recorded'}</td>
              <td data-label="Waiting"><span className="queue-wait"><Clock3 size={13} />{waitingTime(order.sent_to_cashier_at, now)}</span></td>
              <td data-label="Total" className="amount">{formatPrice(order.total)}</td>
              <td><Link to={'/orders/' + order.id} state={{ from: '/cashier/pending' }} className="queue-detail text-link" aria-label={'View order ' + order.id}>View details <ArrowUpRight size={16} /></Link></td>
            </tr>)}</tbody>
          </table>
        </div>}
      </section>
      <p className="table-note">{updated ? 'Updated ' + updated.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : 'Waiting for data'}{error && updated ? ' · Last successful update' : ''}</p>
    </main>
  )
}
