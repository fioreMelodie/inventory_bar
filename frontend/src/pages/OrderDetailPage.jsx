import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getErrorMessage } from '../services/api'
import { ordersService } from '../services/orders'
import { formatPrice } from '../services/products'

/**
 * HU19 - Detalle del pedido recién abierto.
 *
 * El registro de productos y el total se incorporan en la HU20.
 */
export default function OrderDetailPage() {
  const { orderId } = useParams()

  const [order, setOrder] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    loadOrder()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orderId])

  async function loadOrder() {
    setLoading(true)
    try {
      setOrder(await ordersService.retrieve(orderId))
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Unable to load this order.'))
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <main className="mx-auto max-w-3xl px-4 py-8">
        <p className="text-sm text-slate-500">Loading order…</p>
      </main>
    )
  }

  if (error || !order) {
    return (
      <main className="mx-auto max-w-3xl px-4 py-8">
        <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error || 'Order not found.'}
        </p>
        <Link to="/room" className="mt-4 inline-block text-sm text-brand-700 underline">
          Back to the room
        </Link>
      </main>
    )
  }

  return (
    <main className="mx-auto max-w-3xl px-4 py-8">
      <Link to="/room" className="text-sm text-brand-700 underline">
        Back to the room
      </Link>

      <header className="mt-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">
            Order #{order.id} - {order.table_identifier}
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            {order.venue_name} · Opened by {order.waiter_name} ·{' '}
            {new Date(order.opened_at).toLocaleString('en-US')}
          </p>
        </div>

        <span
          className={
            order.status === 'OPEN'
              ? 'rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700'
              : 'rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600'
          }
        >
          {order.status === 'OPEN' ? 'Open' : 'In cashier'}
        </span>
      </header>

      <section className="mt-6 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-medium text-slate-900">Items</h2>
          <p className="text-sm text-slate-500">
            Total: <span className="font-semibold text-slate-900">{formatPrice(order.total)}</span>
          </p>
        </div>

        <p className="mt-3 text-sm text-slate-500">
          No products added yet.
        </p>
      </section>
    </main>
  )
}
