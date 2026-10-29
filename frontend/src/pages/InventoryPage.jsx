import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { getErrorMessage } from '../services/api'
import { inventoryService } from '../services/inventory'
import { productsService } from '../services/products'
import { getFieldError, venuesService } from '../services/venues'

/**
 * HU14 - Registrar entrada de mercancía al inventario.
 * HU15 - Consultar stock disponible por sede.
 * Inventory. Disponible para Cajero (su sede) y Administrador (todas).
 */
export default function InventoryPage() {
  const { user } = useAuth()
  const isAdmin = user.role === 'ADMIN'

  const [products, setProducts] = useState([])
  const [venues, setVenues] = useState([])
  const [loading, setLoading] = useState(true)

  const [venue, setVenue] = useState('')
  const [product, setProduct] = useState('')
  const [quantity, setQuantity] = useState('')
  const [error, setError] = useState('')
  const [feedback, setFeedback] = useState('')
  const [saving, setSaving] = useState(false)

  // HU15 - Consulta de stock de la sede.
  const [stock, setStock] = useState([])
  const [stockVenueName, setStockVenueName] = useState('')
  const [stockSearch, setStockSearch] = useState('')
  const [stockCategory, setStockCategory] = useState('')
  const [stockError, setStockError] = useState('')
  const [loadingStock, setLoadingStock] = useState(true)

  useEffect(() => {
    loadData()
  }, [])

  // El Administrador consulta el stock de la sede seleccionada en el filtro.
  useEffect(() => {
    loadStock()
    const intervalId = setInterval(() => loadStock(true), 10000)
    return () => clearInterval(intervalId)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [venue])

  async function loadData() {
    setLoading(true)
    try {
      const requests = [productsService.list()]
      if (isAdmin) requests.push(venuesService.list())

      const [productList, venueList] = await Promise.all(requests)
      setProducts(productList)
      if (venueList) setVenues(venueList)
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Unable to load the catalog.'))
    } finally {
      setLoading(false)
    }
  }

  const categories = [...new Set(stock.map((item) => item.category))].sort()
  const visibleStock = stock.filter((item) =>
    item.product_name.toLowerCase().includes(stockSearch.trim().toLowerCase()) &&
    (!stockCategory || item.category === stockCategory),
  )

  async function loadStock(background = false) {
    if (!background) setLoadingStock(true)
    try {
      const data = await inventoryService.stock({
        venue: isAdmin && venue ? venue : undefined, background,
      })
      setStock(data.results)
      setStockVenueName(data.venue_name)
      setStockError('')
    } catch (requestError) {
      setStockError(getErrorMessage(requestError, 'Unable to load stock.'))
    } finally {
      setLoadingStock(false)
    }
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setFeedback('')

    if (!product || !quantity) {
      setError('Select a product and enter the quantity received.')
      return
    }

    if (isAdmin && !venue) {
      setError('Select the venue where the goods were received.')
      return
    }

    const units = Number(quantity)
    if (!Number.isInteger(units) || units < 1) {
      setError('Quantity must be a whole number of units, greater than zero.')
      return
    }

    setSaving(true)
    try {
      const stock = await inventoryService.registerEntry({
        product: Number(product),
        quantity: units,
        venue: isAdmin ? Number(venue) : undefined,
      })
      setFeedback(
        'Added ' + units + ' unit' + (units === 1 ? '' : 's') + ' of "' +
          stock.product_name + '" at ' + stock.venue_name +
          '. Stock is now ' + stock.quantity + '.',
      )
      setProduct('')
      setQuantity('')
      await loadStock()
    } catch (requestError) {
      setError(
        getFieldError(requestError, 'quantity') ||
          getFieldError(requestError, 'venue') ||
          getFieldError(requestError, 'product') ||
          getErrorMessage(requestError, 'Unable to register the stock entry.'),
      )
    } finally {
      setSaving(false)
    }
  }

  return (
    <main className="mx-auto max-w-5xl px-4 py-8">
      <header>
        <h1 className="text-xl font-semibold text-slate-900">Inventory</h1>
        <p className="mt-1 text-sm text-slate-500">
          {isAdmin
            ? 'Register incoming goods for any venue. Stock is tracked per venue.'
            : 'Register incoming goods for your venue. Stock is tracked per venue.'}
        </p>
      </header>

      {feedback && (
        <p
          role="status"
          className="mt-4 rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-800"
        >
          {feedback}
        </p>
      )}

      <form
        onSubmit={handleSubmit}
        noValidate
        className="mt-6 rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
      >
        <h2 className="text-base font-medium text-slate-900">Register stock entry</h2>

        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          {isAdmin && (
            <div className="sm:col-span-2">
              <label htmlFor="venue" className="block text-sm font-medium text-slate-700">
                Venue <span className="text-red-500">*</span>
              </label>
              <select
                id="venue"
                value={venue}
                onChange={(event) => setVenue(event.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
              >
                <option value="">Select a venue</option>
                {venues.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div>
            <label htmlFor="product" className="block text-sm font-medium text-slate-700">
              Product <span className="text-red-500">*</span>
            </label>
            <select
              id="product"
              value={product}
              onChange={(event) => setProduct(event.target.value)}
              disabled={loading}
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100 disabled:bg-slate-50"
            >
              <option value="">{loading ? 'Loading products…' : 'Select a product'}</option>
              {products.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="quantity" className="block text-sm font-medium text-slate-700">
              Quantity received <span className="text-red-500">*</span>
            </label>
            <input
              id="quantity"
              type="number"
              min="1"
              step="1"
              value={quantity}
              onChange={(event) => setQuantity(event.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            />
            <p className="mt-1 text-xs text-slate-500">
              Whole units only. Volumes such as ml or liters are not supported.
            </p>
          </div>
        </div>

        {error && (
          <p role="alert" className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}

        <div className="mt-5 flex justify-end">
          <button
            type="submit"
            disabled={saving || loading}
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-brand-700 disabled:bg-slate-300"
          >
            {saving ? 'Registering…' : 'Register entry'}
          </button>
        </div>
      </form>

      <section className="mt-10">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="text-base font-medium text-slate-900">
              Current stock{stockVenueName ? ' - ' + stockVenueName : ''}
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              {isAdmin
                ? 'Pick a venue above to switch the inventory you are looking at.'
                : 'Stock available in your venue.'}
            </p>
          </div>

          <div className="w-full sm:w-64">
            <label htmlFor="stock-category" className="block text-xs font-medium text-slate-600">
              Category
            </label>
            <select
              id="stock-category"
              value={stockCategory}
              onChange={(event) => setStockCategory(event.target.value)}
              className="my-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
            >
              <option value="">All categories</option>
              {categories.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
            <label htmlFor="stock-search" className="block text-xs font-medium text-slate-600">
              Search by product
            </label>
            <input
              id="stock-search"
              type="search"
              value={stockSearch}
              onChange={(event) => setStockSearch(event.target.value)}
              placeholder="Type to filter…"
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            />
          </div>
        </div>

        {stockError && <p role="alert" className="mt-3 text-sm text-red-700">{stockError}</p>}
        <div className="mt-3 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th scope="col" className="px-4 py-3 font-medium">
                    Product
                  </th>
                  <th scope="col" className="px-4 py-3 font-medium">
                    Category
                  </th>
                  <th scope="col" className="px-4 py-3 text-right font-medium">
                    Units in stock
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {loadingStock && (
                  <tr>
                    <td colSpan={3} className="px-4 py-6 text-center text-slate-500">
                      Loading stock…
                    </td>
                  </tr>
                )}

                {!loadingStock && visibleStock.length === 0 && (
                  <tr>
                    <td colSpan={3} className="px-4 py-6 text-center text-slate-500">
                      {stock.length === 0
                        ? 'No products to show yet.'
                        : 'No products match the current filter.'}
                    </td>
                  </tr>
                )}

                {!loadingStock &&
                  visibleStock.map((item) => (
                    <tr
                      key={item.product}
                      className={item.is_out_of_stock ? 'bg-amber-50' : undefined}
                    >
                      <td className="px-4 py-3 font-medium text-slate-900">
                        {item.product_name}
                      </td>
                      <td className="px-4 py-3 text-slate-600">{item.category}</td>
                      <td className="px-4 py-3 text-right">
                        {item.is_out_of_stock ? (
                          <span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-medium text-amber-800">
                            Out of stock
                          </span>
                        ) : (
                          <span className="font-medium text-slate-900">{item.quantity}</span>
                        )}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </main>
  )
}
