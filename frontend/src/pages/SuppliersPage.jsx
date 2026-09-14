import { useEffect, useState } from 'react'
import ConfirmDialog from '../components/ConfirmDialog'
import { getErrorMessage } from '../services/api'
import { suppliersService } from '../services/suppliers'
import { getFieldError } from '../services/venues'

const EMPTY_FORM = { id: null, name: '', phone: '', email: '' }

/**
 * HU12 - Registrar proveedor.
 * Suppliers. Acceso exclusivo del Administrador.
 *
 * El módulo es informativo: no genera órdenes de compra ni afecta el
 * inventario.
 */
export default function SuppliersPage() {
  const [suppliers, setSuppliers] = useState([])
  const [loading, setLoading] = useState(true)

  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState(EMPTY_FORM)
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)
  const [feedback, setFeedback] = useState('')

  const [supplierToDelete, setSupplierToDelete] = useState(null)
  const [deleteError, setDeleteError] = useState('')
  const [deleting, setDeleting] = useState(false)

  const isEditing = form.id !== null

  useEffect(() => {
    loadSuppliers()
  }, [])

  async function loadSuppliers() {
    setLoading(true)
    try {
      setSuppliers(await suppliersService.list())
    } catch (requestError) {
      setFormError(getErrorMessage(requestError, 'Unable to load suppliers.'))
    } finally {
      setLoading(false)
    }
  }

  function openCreateForm() {
    setForm(EMPTY_FORM)
    setFormError('')
    setFeedback('')
    setShowForm(true)
  }

  function openEditForm(supplier) {
    setForm({
      id: supplier.id,
      name: supplier.name,
      phone: supplier.phone ?? '',
      email: supplier.email ?? '',
    })
    setFormError('')
    setFeedback('')
    setShowForm(true)
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setFormError('')
    setFeedback('')

    if (!form.name.trim()) {
      setFormError('Supplier name is required.')
      return
    }

    const payload = {
      name: form.name.trim(),
      phone: form.phone.trim(),
      email: form.email.trim(),
    }

    setSaving(true)
    try {
      if (isEditing) {
        await suppliersService.update(form.id, payload)
        setFeedback('Supplier "' + payload.name + '" was updated successfully.')
      } else {
        await suppliersService.create(payload)
        setFeedback('Supplier "' + payload.name + '" was registered successfully.')
      }
      setShowForm(false)
      setForm(EMPTY_FORM)
      await loadSuppliers()
    } catch (requestError) {
      setFormError(
        getFieldError(requestError, 'name') ||
          getFieldError(requestError, 'email') ||
          getErrorMessage(requestError, 'Unable to save the supplier.'),
      )
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete() {
    setDeleteError('')
    setDeleting(true)
    try {
      await suppliersService.remove(supplierToDelete.id)
      setFeedback('Supplier "' + supplierToDelete.name + '" was deleted.')
      setSupplierToDelete(null)
      await loadSuppliers()
    } catch (requestError) {
      setDeleteError(getErrorMessage(requestError, 'Unable to delete this supplier.'))
    } finally {
      setDeleting(false)
    }
  }

  return (
    <main className="mx-auto max-w-5xl px-4 py-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Suppliers</h1>
          <p className="mt-1 text-sm text-slate-500">
            Reference directory only. Suppliers do not create purchase orders or affect stock.
          </p>
        </div>

        <button
          type="button"
          onClick={showForm ? () => setShowForm(false) : openCreateForm}
          className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
        >
          {showForm ? 'Cancel' : 'New supplier'}
        </button>
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
          <h2 className="text-base font-medium text-slate-900">
            {isEditing ? 'Edit supplier' : 'New supplier'}
          </h2>

          <div className="mt-4 grid gap-4 sm:grid-cols-3">
            <div>
              <label htmlFor="supplier-name" className="block text-sm font-medium text-slate-700">
                Name <span className="text-red-500">*</span>
              </label>
              <input
                id="supplier-name"
                type="text"
                value={form.name}
                onChange={(event) => setForm({ ...form, name: event.target.value })}
                autoFocus
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
              />
            </div>

            <div>
              <label htmlFor="phone" className="block text-sm font-medium text-slate-700">
                Phone <span className="text-slate-400">(optional)</span>
              </label>
              <input
                id="phone"
                type="tel"
                value={form.phone}
                onChange={(event) => setForm({ ...form, phone: event.target.value })}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
              />
            </div>

            <div>
              <label htmlFor="email" className="block text-sm font-medium text-slate-700">
                Email <span className="text-slate-400">(optional)</span>
              </label>
              <input
                id="email"
                type="email"
                value={form.email}
                onChange={(event) => setForm({ ...form, email: event.target.value })}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
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
                  Supplier
                </th>
                <th scope="col" className="px-4 py-3 font-medium">
                  Phone
                </th>
                <th scope="col" className="px-4 py-3 font-medium">
                  Email
                </th>
                <th scope="col" className="px-4 py-3 text-right font-medium">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading && (
                <tr>
                  <td colSpan={4} className="px-4 py-6 text-center text-slate-500">
                    Loading suppliers…
                  </td>
                </tr>
              )}

              {!loading && suppliers.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-4 py-6 text-center text-slate-500">
                    No suppliers registered yet.
                  </td>
                </tr>
              )}

              {!loading &&
                suppliers.map((supplier) => (
                  <tr key={supplier.id}>
                    <td className="px-4 py-3 font-medium text-slate-900">{supplier.name}</td>
                    <td className="px-4 py-3 text-slate-600">{supplier.phone || '-'}</td>
                    <td className="px-4 py-3 text-slate-600">{supplier.email || '-'}</td>
                    <td className="px-4 py-3">
                      <div className="flex justify-end gap-2">
                        <button
                          type="button"
                          onClick={() => openEditForm(supplier)}
                          className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:bg-slate-50"
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            setDeleteError('')
                            setSupplierToDelete(supplier)
                          }}
                          className="rounded-lg border border-red-200 px-3 py-1.5 text-xs font-medium text-red-700 transition hover:bg-red-50"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </section>

      {supplierToDelete && (
        <ConfirmDialog
          title={'Delete "' + supplierToDelete.name + '"?'}
          message="The supplier will be removed from the directory. Products linked to it keep
            working normally; only the supplier reference is cleared."
          confirmLabel="Delete"
          error={deleteError}
          busy={deleting}
          onConfirm={handleDelete}
          onCancel={() => setSupplierToDelete(null)}
        />
      )}
    </main>
  )
}
