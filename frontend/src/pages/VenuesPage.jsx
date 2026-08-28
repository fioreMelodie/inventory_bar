import { useEffect, useState } from 'react'
import { getErrorMessage } from '../services/api'
import { getFieldError, venuesService } from '../services/venues'

/**
 * HU04 - Crear sede.
 * Administración > Venues. Acceso exclusivo del Administrador.
 */
export default function VenuesPage() {
  const [venues, setVenues] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [name, setName] = useState('')
  const [address, setAddress] = useState('')
  const [error, setError] = useState('')
  const [feedback, setFeedback] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    loadVenues()
  }, [])

  async function loadVenues() {
    setLoading(true)
    try {
      setVenues(await venuesService.list())
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Unable to load venues.'))
    } finally {
      setLoading(false)
    }
  }

  function resetForm() {
    setName('')
    setAddress('')
    setError('')
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setFeedback('')

    if (!name.trim()) {
      setError('Venue name is required.')
      return
    }

    setSaving(true)
    try {
      const venue = await venuesService.create({ name: name.trim(), address: address.trim() })
      setVenues((current) => [...current, venue].sort((a, b) => a.name.localeCompare(b.name)))
      setFeedback('Venue "' + venue.name + '" was created successfully.')
      resetForm()
      setShowForm(false)
    } catch (requestError) {
      setError(
        getFieldError(requestError, 'name') ||
          getErrorMessage(requestError, 'Unable to create the venue.'),
      )
    } finally {
      setSaving(false)
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
          onClick={() => {
            resetForm()
            setFeedback('')
            setShowForm((current) => !current)
          }}
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

      {showForm && (
        <form
          onSubmit={handleSubmit}
          noValidate
          className="mt-6 rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
        >
          <h2 className="text-base font-medium text-slate-900">New venue</h2>

          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="venue-name" className="block text-sm font-medium text-slate-700">
                Name <span className="text-red-500">*</span>
              </label>
              <input
                id="venue-name"
                type="text"
                value={name}
                onChange={(event) => setName(event.target.value)}
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
                value={address}
                onChange={(event) => setAddress(event.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
              />
            </div>
          </div>

          {error && (
            <p role="alert" className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
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
                  Name
                </th>
                <th scope="col" className="px-4 py-3 font-medium">
                  Address
                </th>
                <th scope="col" className="px-4 py-3 font-medium">
                  Status
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading && (
                <tr>
                  <td colSpan={3} className="px-4 py-6 text-center text-slate-500">
                    Loading venues…
                  </td>
                </tr>
              )}

              {!loading && venues.length === 0 && (
                <tr>
                  <td colSpan={3} className="px-4 py-6 text-center text-slate-500">
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
                      <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700">
                        Active
                      </span>
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
