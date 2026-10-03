import { useEffect, useState } from 'react'
import ConfirmDialog from '../components/ConfirmDialog'
import { getErrorMessage } from '../services/api'
import { tablesService } from '../services/tables'
import { getFieldError, venuesService } from '../services/venues'

/**
 * HU17 - Crear y configurar mesas por sede.
 * Administración > Tables. Acceso exclusivo del Administrador.
 */
export default function TablesPage() {
  const [venues, setVenues] = useState([])
  const [venue, setVenue] = useState('')
  const [tables, setTables] = useState([])
  const [loading, setLoading] = useState(true)
  const [includeInactive, setIncludeInactive] = useState(false)

  const [identifier, setIdentifier] = useState('')
  const [editingId, setEditingId] = useState(null)
  const [error, setError] = useState('')
  const [feedback, setFeedback] = useState('')
  const [saving, setSaving] = useState(false)

  const [tableToDeactivate, setTableToDeactivate] = useState(null)
  const [deactivationError, setDeactivationError] = useState('')
  const [deactivating, setDeactivating] = useState(false)

  useEffect(() => {
    loadVenues()
  }, [])

  useEffect(() => {
    if (venue) loadTables()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [venue, includeInactive])

  async function loadVenues() {
    try {
      const list = await venuesService.list()
      setVenues(list)
      if (list.length > 0) setVenue(String(list[0].id))
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Unable to load venues.'))
    } finally {
      setLoading(false)
    }
  }

  async function loadTables() {
    setLoading(true)
    try {
      setTables(await tablesService.list({ venue, includeInactive }))
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Unable to load tables.'))
    } finally {
      setLoading(false)
    }
  }

  function startEdit(table) {
    setEditingId(table.id)
    setIdentifier(table.identifier)
    setError('')
    setFeedback('')
  }

  function cancelEdit() {
    setEditingId(null)
    setIdentifier('')
    setError('')
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setFeedback('')

    if (!identifier.trim()) {
      setError('Table identifier is required.')
      return
    }

    setSaving(true)
    try {
      if (editingId) {
        await tablesService.update(editingId, { identifier: identifier.trim() })
        setFeedback('Table "' + identifier.trim() + '" was renamed.')
      } else {
        await tablesService.create({ venue: Number(venue), identifier: identifier.trim() })
        setFeedback('Table "' + identifier.trim() + '" was created.')
      }
      cancelEdit()
      await loadTables()
    } catch (requestError) {
      setError(
        getFieldError(requestError, 'identifier') ||
          getErrorMessage(requestError, 'Unable to save the table.'),
      )
    } finally {
      setSaving(false)
    }
  }

  async function handleDeactivate() {
    setDeactivationError('')
    setDeactivating(true)
    try {
      await tablesService.deactivate(tableToDeactivate.id)
      setFeedback('Table "' + tableToDeactivate.identifier + '" is now inactive.')
      setTableToDeactivate(null)
      await loadTables()
    } catch (requestError) {
      setDeactivationError(
        getErrorMessage(requestError, 'Unable to deactivate this table.'),
      )
    } finally {
      setDeactivating(false)
    }
  }

  return (
    <main className="mx-auto max-w-4xl px-4 py-8">
      <header>
        <h1 className="text-xl font-semibold text-slate-900">Tables</h1>
        <p className="mt-1 text-sm text-slate-500">
          Set up the floor plan of each venue. There is no limit on the number of tables.
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
        <h2 className="text-base font-medium text-slate-900">
          {editingId ? 'Rename table' : 'New table'}
        </h2>

        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="venue" className="block text-sm font-medium text-slate-700">
              Venue <span className="text-red-500">*</span>
            </label>
            <select
              id="venue"
              value={venue}
              onChange={(event) => {
                setVenue(event.target.value)
                cancelEdit()
              }}
              disabled={Boolean(editingId)}
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100 disabled:bg-slate-50"
            >
              {venues.length === 0 && <option value="">No venues registered</option>}
              {venues.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="identifier" className="block text-sm font-medium text-slate-700">
              Table identifier <span className="text-red-500">*</span>
            </label>
            <input
              id="identifier"
              type="text"
              value={identifier}
              onChange={(event) => setIdentifier(event.target.value)}
              placeholder="Table 1"
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            />
            <p className="mt-1 text-xs text-slate-500">
              Must be unique within the venue.
            </p>
          </div>
        </div>

        {error && (
          <p role="alert" className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}

        <div className="mt-5 flex justify-end gap-2">
          {editingId && (
            <button
              type="button"
              onClick={cancelEdit}
              className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
            >
              Cancel
            </button>
          )}
          <button
            type="submit"
            disabled={saving || !venue}
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-brand-700 disabled:bg-slate-300"
          >
            {saving ? 'Saving…' : editingId ? 'Save' : 'Add table'}
          </button>
        </div>
      </form>

      <label className="mt-6 flex items-center gap-2 text-sm text-slate-600">
        <input
          type="checkbox"
          checked={includeInactive}
          onChange={(event) => setIncludeInactive(event.target.checked)}
          className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
        />
        Show inactive tables
      </label>

      <section className="mt-3 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th scope="col" className="px-4 py-3 font-medium">
                  Table
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
                  <td colSpan={3} className="px-4 py-6 text-center text-slate-500">
                    Loading tables…
                  </td>
                </tr>
              )}

              {!loading && tables.length === 0 && (
                <tr>
                  <td colSpan={3} className="px-4 py-6 text-center text-slate-500">
                    This venue has no tables yet.
                  </td>
                </tr>
              )}

              {!loading &&
                tables.map((table) => (
                  <tr key={table.id}>
                    <td className="px-4 py-3 font-medium text-slate-900">
                      {table.identifier}
                      {!table.is_active && (
                        <span className="ml-2 rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                          Inactive
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={
                          table.status === 'FREE'
                            ? 'rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700'
                            : 'rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-800'
                        }
                      >
                        {table.status === 'FREE' ? 'Free' : 'Occupied'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex justify-end gap-2">
                        <button
                          type="button"
                          onClick={() => startEdit(table)}
                          disabled={table.status !== 'FREE'}
                          className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
                        >
                          Rename
                        </button>
                        {table.is_active && (
                          <button
                            type="button"
                            onClick={() => {
                              setDeactivationError('')
                              setTableToDeactivate(table)
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

      {tableToDeactivate && (
        <ConfirmDialog
          title={'Deactivate "' + tableToDeactivate.identifier + '"?'}
          message="The table will no longer accept new orders. Tables are never deleted, so its
            order history stays available."
          confirmLabel="Deactivate"
          error={deactivationError}
          busy={deactivating}
          onConfirm={handleDeactivate}
          onCancel={() => setTableToDeactivate(null)}
        />
      )}
    </main>
  )
}
