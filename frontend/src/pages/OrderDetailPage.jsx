import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { getErrorMessage } from '../services/api'
import { ordersService } from '../services/orders'
import { formatPrice, productsService } from '../services/products'

/**
 * HU19 - Detalle del pedido abierto.
 * HU20 - Agregar productos y cantidades al pedido.
 */
export default function OrderDetailPage() {
  const { orderId } = useParams()
  const { user } = useAuth()

  const [order, setOrder] = useState(null)
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('')
  const [quantities, setQuantities] = useState({})
  const [adding, setAdding] = useState(null)

  const isOpen = order?.status === 'OPEN'
  const canEdit = isOpen && (order?.waiter === user.id || user.role === 'ADMIN')

  useEffect(() => {
    loadData()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orderId])

  async function loadData() {
    setLoading(true)
    try {
      const [orderData, productList] = await Promise.all([
        ordersService.retrieve(orderId),
        productsService.list(),
      ])
      setOrder(orderData)
      setProducts(productList)
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Unable to load this order.'))
    } finally {
      setLoading(false)
    }
  }

  async function addProduct(product) {
    setError('')
    const quantity = Number(quantities[product.id] ?? 1)

    if (!Number.isInteger(quantity) || quantity < 1) {
      setError('Quantity must be a whole number of units, greater than zero.')
      return
    }

    setAdding(product.id)
    try {
      const updated = await ordersService.addItem(order.id, product.id, quantity)
      setOrder(updated)
      setQuantities({ ...quantities, [product.id]: '' })
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Unable to add this product.'))
    } finally {
      setAdding(null)
    }
  }

  const categories = [...new Set(products.map((product) => product.category))].sort()

  const visibleProducts = products.filter((product) => {
    const matchesSearch = product.name.toLowerCase().includes(search.trim().toLowerCase())
    const matchesCategory = !category || product.category === category
    return matchesSearch && matchesCategory
  })

  if (loading) {
    return (
      <main className="mx-auto max-w-4xl px-4 py-8">
        <p className="text-sm text-slate-500">Loading order…</p>
      </main>
    )
  }

  if (!order) {
    return (
      <main className="mx-auto max-w-4xl px-4 py-8">
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
    <main className="mx-auto max-w-4xl px-4 py-8">
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
            isOpen
              ? 'rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700'
              : 'rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600'
          }
        >
          {order.status_label}
        </span>
      </header>

      {error && (
        <p role="alert" className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      <section className="mt-6 rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="flex items-center justify-between border-b border-slate-200 p-5">
          <h2 className="text-base font-medium text-slate-900">Items</h2>
          <p className="text-sm text-slate-500">
            Total:{' '}
            <span className="text-base font-semibold text-slate-900">
              {formatPrice(order.total)}
            </span>
          </p>
        </div>

        {order.items.length === 0 ? (
          <p className="p-5 text-sm text-slate-500">No products added yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th scope="col" className="px-4 py-3 font-medium">
                    Product
                  </th>
                  <th scope="col" className="px-4 py-3 text-right font-medium">
                    Qty
                  </th>
                  <th scope="col" className="px-4 py-3 text-right font-medium">
                    Unit price
                  </th>
                  <th scope="col" className="px-4 py-3 text-right font-medium">
                    Subtotal
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {order.items.map((item) => (
                  <tr key={item.id}>
                    <td className="px-4 py-3 font-medium text-slate-900">
                      {item.product_name}
                    </td>
                    <td className="px-4 py-3 text-right text-slate-600">{item.quantity}</td>
                    <td className="px-4 py-3 text-right text-slate-600">
                      {formatPrice(item.unit_price)}
                    </td>
                    <td className="px-4 py-3 text-right font-medium text-slate-900">
                      {formatPrice(item.subtotal)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {canEdit && (
        <section className="mt-8">
          <h2 className="text-base font-medium text-slate-900">Add products</h2>

          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <div>
              <label htmlFor="search" className="block text-xs font-medium text-slate-600">
                Search by name
              </label>
              <input
                id="search"
                type="search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Type to filter…"
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
              />
            </div>

            <div>
              <label htmlFor="category" className="block text-xs font-medium text-slate-600">
                Category
              </label>
              <select
                id="category"
                value={category}
                onChange={(event) => setCategory(event.target.value)}
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

          <ul className="mt-4 divide-y divide-slate-100 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
            {visibleProducts.length === 0 && (
              <li className="p-5 text-sm text-slate-500">No products match the filter.</li>
            )}

            {visibleProducts.map((product) => (
              <li key={product.id} className="flex flex-wrap items-center gap-3 p-4">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-slate-900">{product.name}</p>
                  <p className="text-xs text-slate-500">
                    {product.category} · {formatPrice(product.sale_price)}
                  </p>
                </div>

                <input
                  type="number"
                  min="1"
                  step="1"
                  aria-label={'Quantity of ' + product.name}
                  value={quantities[product.id] ?? ''}
                  onChange={(event) =>
                    setQuantities({ ...quantities, [product.id]: event.target.value })
                  }
                  placeholder="1"
                  className="w-20 rounded-lg border border-slate-300 px-3 py-1.5 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
                />

                <button
                  type="button"
                  onClick={() => addProduct(product)}
                  disabled={adding === product.id}
                  className="rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-brand-700 disabled:bg-slate-300"
                >
                  {adding === product.id ? 'Adding…' : 'Add'}
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      {!isOpen && (
        <p className="mt-6 rounded-lg bg-slate-100 px-3 py-2 text-sm text-slate-600">
          This order has been sent to the cashier and can no longer be modified.
        </p>
      )}
    </main>
  )
}
