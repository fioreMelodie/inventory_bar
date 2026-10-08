import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { ordersService } from '../services/orders'
import { formatPrice } from '../services/products'
import { getErrorMessage } from '../services/api'

/**
 * Menú principal al que se redirige tras iniciar sesión.
 * Las opciones de cada rol se incorporan en las historias siguientes.
 */
export default function HomePage() {
  const { user } = useAuth()
  const [orders, setOrders] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (user.role !== 'CASHIER') return undefined
    let cancelled = false
    async function load(background = false) {
      try {
        const pending = await ordersService.list({ status: 'IN_CASHIER', background })
        if (!cancelled) {
          setOrders(pending)
          setError('')
        }
      } catch (requestError) {
        if (!cancelled) setError(getErrorMessage(requestError, 'Unable to load pending orders.'))
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    const intervalId = setInterval(() => load(true), 5000)
    return () => { cancelled = true; clearInterval(intervalId) }
  }, [user.role])

  return (
    <main className="mx-auto max-w-4xl px-4 py-10">
      <header className="border-b border-slate-200 pb-6">
        <h1 className="text-xl font-semibold text-slate-900">
          Welcome, {user.full_name.split(' ')[0]}
        </h1>
      </header>

      <section className="mt-8">
        {user.role === 'CASHIER' ? (
          <>
            <h2 className="text-base font-medium text-slate-900">Pending orders</h2>
            {error && <p role="alert" className="mt-3 text-sm text-red-700">{error}</p>}
            {loading && <p className="mt-3 text-sm text-slate-500">Loading orders...</p>}
            {!loading && !error && orders.length === 0 && (
              <p className="mt-3 text-sm text-slate-500">No pending orders.</p>
            )}
            <ul className="mt-3 divide-y divide-slate-200">
              {orders.map((order) => (
                <li key={order.id} className="flex flex-wrap items-center justify-between gap-3 py-4">
                  <Link to={'/orders/' + order.id} className="text-sm font-medium text-brand-700 underline">
                    Order #{order.id} - {order.table_identifier}
                  </Link>
                  <span className="text-sm text-slate-700">{formatPrice(order.total)}</span>
                </li>
              ))}
            </ul>
          </>
        ) : (
          <Link to="/room" className="text-sm font-medium text-brand-700 underline">Room</Link>
        )}
      </section>
    </main>
  )
}
