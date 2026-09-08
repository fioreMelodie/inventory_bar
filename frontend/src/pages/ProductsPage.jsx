import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { getErrorMessage } from '../services/api'
import { formatPrice, productsService } from '../services/products'
import { getFieldError } from '../services/venues'

const EMPTY_FORM = {
  name: '',
  product_type: '',
  category: '',
  purchase_price: '',
  sale_price: '',
}

/**
 * HU09 - Crear producto en el catálogo.
 * Productos > Catalog. La creación es exclusiva del Administrador.
 */
export default function ProductsPage() {
  const { user } = useAuth()
  const isAdmin = user.role === 'ADMIN'

  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)

  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState(EMPTY_FORM)
  const [image, setImage] = useState(null)
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)
  const [feedback, setFeedback] = useState('')

  useEffect(() => {
    loadProducts()
  }, [])

  async function loadProducts() {
    setLoading(true)
    try {
      setProducts(await productsService.list())
    } catch (requestError) {
      setFormError(getErrorMessage(requestError, 'Unable to load the catalog.'))
    } finally {
      setLoading(false)
    }
  }

  function openForm() {
    setForm(EMPTY_FORM)
    setImage(null)
    setFormError('')
    setFeedback('')
    setShowForm(true)
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setFormError('')
    setFeedback('')

    if (
      !form.name.trim() ||
      !form.product_type.trim() ||
      !form.category.trim() ||
      !form.purchase_price ||
      !form.sale_price
    ) {
      setFormError('Please complete all required fields.')
      return
    }

    setSaving(true)
    try {
      await productsService.create(
        {
          name: form.name.trim(),
          product_type: form.product_type.trim(),
          category: form.category.trim(),
          purchase_price: Number(form.purchase_price),
          sale_price: Number(form.sale_price),
        },
        image,
      )
      setFeedback('Product "' + form.name.trim() + '" was created successfully.')
      setShowForm(false)
      setForm(EMPTY_FORM)
      setImage(null)
      await loadProducts()
    } catch (requestError) {
      setFormError(
        getFieldError(requestError, 'name') ||
          getFieldError(requestError, 'purchase_price') ||
          getFieldError(requestError, 'sale_price') ||
          getErrorMessage(requestError, 'Unable to save the product.'),
      )
    } finally {
      setSaving(false)
    }
  }

  return (
    <main className="mx-auto max-w-5xl px-4 py-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Catalog</h1>
          <p className="mt-1 text-sm text-slate-500">
            One shared catalog for every venue. Prices are the same everywhere; stock is
            managed per venue.
          </p>
        </div>

        {isAdmin && (
          <button
            type="button"
            onClick={showForm ? () => setShowForm(false) : openForm}
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
          >
            {showForm ? 'Cancel' : 'New product'}
          </button>
        )}
      </div>

      {feedback && (
        <p
          role="status"
          className="mt-4 rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-800"
        >
          {feedback}
        </p>
      )}

      {showForm && (
        <form
          onSubmit={handleSubmit}
          noValidate
          className="mt-6 rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
        >
          <h2 className="text-base font-medium text-slate-900">New product</h2>

          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <label htmlFor="product-name" className="block text-sm font-medium text-slate-700">
                Name <span className="text-red-500">*</span>
              </label>
              <input
                id="product-name"
                type="text"
                value={form.name}
                onChange={(event) => setForm({ ...form, name: event.target.value })}
                autoFocus
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
              />
            </div>

            <div>
              <label htmlFor="product-type" className="block text-sm font-medium text-slate-700">
                Type <span className="text-red-500">*</span>
              </label>
              <input
                id="product-type"
                type="text"
                placeholder="Beer, spirits, snack…"
                value={form.product_type}
                onChange={(event) => setForm({ ...form, product_type: event.target.value })}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
              />
            </div>

            <div>
              <label htmlFor="category" className="block text-sm font-medium text-slate-700">
                Category <span className="text-red-500">*</span>
              </label>
              <input
                id="category"
                type="text"
                value={form.category}
                onChange={(event) => setForm({ ...form, category: event.target.value })}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
              />
            </div>

            <div>
              <label
                htmlFor="purchase-price"
                className="block text-sm font-medium text-slate-700"
              >
                Purchase price <span className="text-red-500">*</span>
              </label>
              <input
                id="purchase-price"
                type="number"
                min="1"
                step="1"
                value={form.purchase_price}
                onChange={(event) => setForm({ ...form, purchase_price: event.target.value })}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
              />
            </div>

            <div>
              <label htmlFor="sale-price" className="block text-sm font-medium text-slate-700">
                Sale price <span className="text-red-500">*</span>
              </label>
              <input
                id="sale-price"
                type="number"
                min="1"
                step="1"
                value={form.sale_price}
                onChange={(event) => setForm({ ...form, sale_price: event.target.value })}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
              />
            </div>

            <div className="sm:col-span-2">
              <label htmlFor="image" className="block text-sm font-medium text-slate-700">
                Image <span className="text-slate-400">(optional)</span>
              </label>
              <input
                id="image"
                type="file"
                accept="image/*"
                onChange={(event) => setImage(event.target.files?.[0] ?? null)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm file:mr-3 file:rounded file:border-0 file:bg-slate-100 file:px-3 file:py-1 file:text-sm"
              />
            </div>
          </div>

          {formError && (
            <p role="alert" className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
              {formError}
            </p>
          )}

          <div className="mt-5 flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-brand-700 disabled:bg-slate-300"
            >
              {saving ? 'Saving…' : 'Save'}
            </button>
          </div>
        </form>
      )}

      <section className="mt-6 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th scope="col" className="px-4 py-3 font-medium">
                  Product
                </th>
                <th scope="col" className="px-4 py-3 font-medium">
                  Type
                </th>
                <th scope="col" className="px-4 py-3 font-medium">
                  Category
                </th>
                {isAdmin && (
                  <th scope="col" className="px-4 py-3 text-right font-medium">
                    Purchase
                  </th>
                )}
                <th scope="col" className="px-4 py-3 text-right font-medium">
                  Sale price
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading && (
                <tr>
                  <td colSpan={isAdmin ? 5 : 4} className="px-4 py-6 text-center text-slate-500">
                    Loading catalog…
                  </td>
                </tr>
              )}

              {!loading && products.length === 0 && (
                <tr>
                  <td colSpan={isAdmin ? 5 : 4} className="px-4 py-6 text-center text-slate-500">
                    No products in the catalog yet.
                  </td>
                </tr>
              )}

              {!loading &&
                products.map((product) => (
                  <tr key={product.id}>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        {product.image ? (
                          <img
                            src={product.image}
                            alt=""
                            className="h-9 w-9 rounded object-cover"
                          />
                        ) : (
                          <span
                            aria-hidden="true"
                            className="flex h-9 w-9 items-center justify-center rounded bg-slate-100 text-slate-400"
                          >
                            &#9634;
                          </span>
                        )}
                        <span className="font-medium text-slate-900">{product.name}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-slate-600">{product.product_type}</td>
                    <td className="px-4 py-3 text-slate-600">{product.category}</td>
                    {isAdmin && (
                      <td className="px-4 py-3 text-right text-slate-600">
                        {formatPrice(product.purchase_price)}
                      </td>
                    )}
                    <td className="px-4 py-3 text-right font-medium text-slate-900">
                      {formatPrice(product.sale_price)}
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
