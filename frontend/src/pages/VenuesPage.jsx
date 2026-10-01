import { useEffect, useState } from 'react'
import ConfirmDialog from '../components/ConfirmDialog'
import { getErrorMessage } from '../services/api'
import { getFieldError, venuesService } from '../services/venues'

const EMPTY_FORM = { id: null, name: '', address: '' }

/**
 * HU04 - Crear sede · HU05 - Editar e inactivar sede.
 * Administración > Venues. Acceso exclusivo del Administrador.
 */
export default function VenuesPage() {
  const [venues, setVenues] = useState([])
  const [loading, setLoading] = useState(true)
  const [includeInactive, setIncludeInactive] = useState(false)

  const [form, setForm] = useState(EMPTY_FORM)
  const [showForm, setShowForm] = useState(false)
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)

  const [venueToDeactivate, setVenueToDeactivate] = useState(null)
  const [deactivationError, setDeactivationError] = useState('')
  const [deactivating, setDeactivating] = useState(false)

  const [feedback, setFeedback] = useState('')
  const [listError, setListError] = useState('')

  const isEditing = form.id !== null

  useEffect(() => {
    loadVenues()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [includeInactive])

  async function loadVenues(showInactive = includeInactive) {
    setLoading(true)
    setListError('')
    try {
      setVenues(await venuesService.list({ includeInactive: showInactive }))
    } catch (requestError) {
      setListError(getErrorMessage(requestError, 'Unable to load venues.'))
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

  function openEditForm(venue) {
    setForm({ id: venue.id, name: venue.name, address: venue.address ?? '' })
    setFormError('')
    setFeedback('')
    setShowForm(true)
  }

  function closeForm() {
    setShowForm(false)
    setForm(EMPTY_FORM)
    setFormError('')
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setFormError('')
    setFeedback('')

    if (!form.name.trim()) {
      setFormError('Venue name is required.')
      return
    }

    const payload = { name: form.name.trim(), address: form.address.trim() }
    setSaving(true)
    try {
      if (isEditing) {
        await venuesService.update(form.id, payload)
        setFeedback('Venue "' + payload.name + '" was updated successfully.')
      } else {
        await venuesService.create(payload)
        setFeedback('Venue "' + payload.name + '" was created successfully.')
      }
      closeForm()
      await loadVenues()
    } catch (requestError) {
      setFormError(
        getFieldError(requestError, 'name') ||
          getErrorMessage(requestError, 'Unable to save the venue.'),
      )
    } finally {
      setSaving(false)
    }
  }

  async function handleDeactivate() {
    setDeactivationError('')
    setDeactivating(true)
    try {
      await venuesService.deactivate(venueToDeactivate.id)
      setFeedback(
        'Venue "' + venueToDeactivate.name +
          '" is now inactive. Its history is kept and it can be reactivated.',
      )
      setVenueToDeactivate(null)
      // La sede no se elimina: se muestran las inactivas para que siga visible.
      setIncludeInactive(true)
      await loadVenues(true)
    } catch (requestError) {
      setDeactivationError(
        getErrorMessage(requestError, 'Unable to deactivate this venue.'),
      )
    } finally {
      setDeactivating(false)
    }
  }

  return (
    <main className="mx-auto max-w-5xl px-4 py-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Venues</h1>
          <p className="mt-1 text-sm text-slate-500">
            Each venue operates independently, with its own tables, inventory and users.
          </p>
        </div>

        <button
          type="button"
          onClick={showForm ? closeForm : openCreateForm}
          className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
        >
          {showForm ? 'Cancel' : 'New venue'}
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

      {listError && (
        <p role="alert" className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {listError}
        </p>
      )}

      {showForm && (
        <form
          onSubmit={handleSubmit}
          noValidate
          className="mt-6 rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
        >
          <h2 className="text-base font-medium text-slate-900">
            {isEditing ? 'Edit venue' : 'New venue'}
          </h2>

          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="venue-name" className="block text-sm font-medium text-slate-700">
                Name <span className="text-red-500">*</span>
              </label>
              <input
                id="venue-name"
                type="text"
                value={form.name}
                onChange={(event) => setForm({ ...form, name: event.target.value })}
                autoFocus
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
              />
            </div>

            <div>
              <label htmlFor="venue-address" className="block text-sm font-medium text-slate-700">
                Address <span className="text-slate-400">(optional)</span>
              </label>
              <input
                id="venue-address"
                type="text"
                value={form.address}
                onChange={(event) => setForm({ ...form, address: event.target.value })}
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
              onClick={closeForm}
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

      <label className="mt-6 flex items-center gap-2 text-sm text-slate-600">
        <input
          type="checkbox"
          checked={includeInactive}
          onChange={(event) => setIncludeInactive(event.target.checked)}
          className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
        />
        Show inactive venues
      </label>

      <section className="mt-3 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th scope="col" className="px-4 py-3 font-medium">
                  Name
                </th>
                <th scope="col" className="px-4 py-3 font-medium">
                  Address
                </th>
                <th scope="col" className="px-4 py-3 font-medium">
                  Status
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
                    Loading venues…
                  </td>
                </tr>
              )}

              {!loading && venues.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-4 py-6 text-center text-slate-500">
                    No venues registered yet.
                  </td>
                </tr>
              )}

              {!loading &&
                venues.map((venue) => (
                  <tr key={venue.id}>
                    <td className="px-4 py-3 font-medium text-slate-900">{venue.name}</td>
                    <td className="px-4 py-3 text-slate-600">{venue.address || '—'}</td>
                    <td className="px-4 py-3">
                      <span
                        className={
                          venue.is_active
                            ? 'rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700'
                            : 'rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600'
                        }
                      >
                        {venue.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex justify-end gap-2">
                        <button
                          type="button"
                          onClick={() => openEditForm(venue)}
                          className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:bg-slate-50"
                        >
                          Edit
                        </button>
                        {venue.is_active && (
                          <button
                            type="button"
                            onClick={() => {
                              setDeactivationError('')
                              setVenueToDeactivate(venue)
                            }}
                            className="rounded-lg border border-red-200 px-3 py-1.5 text-xs font-medium text-red-700 transition hover:bg-red-50"
                          >
                            Deactivate
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </section>

      {venueToDeactivate && (
        <ConfirmDialog
          title={'Deactivate "' + venueToDeactivate.name + '"?'}
          message="The venue will no longer be available for new users, tables or orders. Its
            reports and history remain accessible. Users assigned to this venue will need to be
            reassigned."
          confirmLabel="Deactivate"
          error={deactivationError}
          busy={deactivating}
          onConfirm={handleDeactivate}
          onCancel={() => setVenueToDeactivate(null)}
        />
      )}
    </main>
  )
}
