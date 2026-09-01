import { useEffect, useState } from 'react'
import { getErrorMessage } from '../services/api'
import { ROLES_REQUIRING_VENUE, ROLE_OPTIONS, usersService } from '../services/users'
import { getFieldError, venuesService } from '../services/venues'

const EMPTY_FORM = {
  full_name: '',
  username: '',
  password: '',
  role: '',
  venue: '',
}

/**
 * HU06 - Crear usuario con rol y sede asignada.
 * Administración > Users. Acceso exclusivo del Administrador.
 */
export default function UsersPage() {
  const [users, setUsers] = useState([])
  const [venues, setVenues] = useState([])
  const [loading, setLoading] = useState(true)

  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState(EMPTY_FORM)
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)
  const [feedback, setFeedback] = useState('')

  const venueRequired = ROLES_REQUIRING_VENUE.includes(form.role)

  useEffect(() => {
    loadData()
  }, [])

  async function loadData() {
    setLoading(true)
    try {
      const [userList, venueList] = await Promise.all([
        usersService.list(),
        venuesService.list(),
      ])
      setUsers(userList)
      setVenues(venueList)
    } catch (requestError) {
      setFormError(getErrorMessage(requestError, 'Unable to load users.'))
    } finally {
      setLoading(false)
    }
  }

  function openForm() {
    setForm(EMPTY_FORM)
    setFormError('')
    setFeedback('')
    setShowForm(true)
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setFormError('')
    setFeedback('')

    if (!form.full_name.trim() || !form.username.trim() || !form.password || !form.role) {
      setFormError('Please complete all required fields.')
      return
    }

    if (venueRequired && !form.venue) {
      setFormError('Cashiers and waiters must be assigned to a venue.')
      return
    }

    setSaving(true)
    try {
      await usersService.create({
        full_name: form.full_name.trim(),
        username: form.username.trim(),
        password: form.password,
        role: form.role,
        venue: form.venue || null,
      })
      setFeedback('User "' + form.username.trim() + '" was created successfully.')
      setShowForm(false)
      setForm(EMPTY_FORM)
      await loadData()
    } catch (requestError) {
      setFormError(
        getFieldError(requestError, 'username') ||
          getFieldError(requestError, 'password') ||
          getFieldError(requestError, 'venue') ||
          getErrorMessage(requestError, 'Unable to create the user.'),
      )
    } finally {
      setSaving(false)
    }
  }

  return (
    <main className="mx-auto max-w-5xl px-4 py-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Users</h1>
          <p className="mt-1 text-sm text-slate-500">
            Accounts are created here. Self-registration is not available.
          </p>
        </div>

        <button
          type="button"
          onClick={showForm ? () => setShowForm(false) : openForm}
          className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
        >
          {showForm ? 'Cancel' : 'New user'}
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
          <h2 className="text-base font-medium text-slate-900">New user</h2>

          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="full-name" className="block text-sm font-medium text-slate-700">
                Full name <span className="text-red-500">*</span>
              </label>
              <input
                id="full-name"
                type="text"
                value={form.full_name}
                onChange={(event) => setForm({ ...form, full_name: event.target.value })}
                autoFocus
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
              />
            </div>

            <div>
              <label htmlFor="username" className="block text-sm font-medium text-slate-700">
                Username <span className="text-red-500">*</span>
              </label>
              <input
                id="username"
                type="text"
                autoComplete="off"
                value={form.username}
                onChange={(event) => setForm({ ...form, username: event.target.value })}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-slate-700">
                Temporary password <span className="text-red-500">*</span>
              </label>
              <input
                id="password"
                type="password"
                autoComplete="new-password"
                value={form.password}
                onChange={(event) => setForm({ ...form, password: event.target.value })}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
              />
              <p className="mt-1 text-xs text-slate-500">At least 8 characters.</p>
            </div>

            <div>
              <label htmlFor="role" className="block text-sm font-medium text-slate-700">
                Role <span className="text-red-500">*</span>
              </label>
              <select
                id="role"
                value={form.role}
                onChange={(event) =>
                  setForm({
                    ...form,
                    role: event.target.value,
                    venue: event.target.value === 'ADMIN' ? '' : form.venue,
                  })
                }
                className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
              >
                <option value="">Select a role</option>
                {ROLE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="sm:col-span-2">
              <label htmlFor="venue" className="block text-sm font-medium text-slate-700">
                Venue{' '}
                {venueRequired ? (
                  <span className="text-red-500">*</span>
                ) : (
                  <span className="text-slate-400">(optional for administrators)</span>
                )}
              </label>
              <select
                id="venue"
                value={form.venue}
                onChange={(event) => setForm({ ...form, venue: event.target.value })}
                className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
              >
                <option value="">No venue assigned</option>
                {venues.map((venue) => (
                  <option key={venue.id} value={venue.id}>
                    {venue.name}
                  </option>
                ))}
              </select>
              <p className="mt-1 text-xs text-slate-500">
                Cashiers and waiters only see information from their assigned venue.
              </p>
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
                  Full name
                </th>
                <th scope="col" className="px-4 py-3 font-medium">
                  Username
                </th>
                <th scope="col" className="px-4 py-3 font-medium">
                  Role
                </th>
                <th scope="col" className="px-4 py-3 font-medium">
                  Venue
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading && (
                <tr>
                  <td colSpan={4} className="px-4 py-6 text-center text-slate-500">
                    Loading users…
                  </td>
                </tr>
              )}

              {!loading && users.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-4 py-6 text-center text-slate-500">
                    No users registered yet.
                  </td>
                </tr>
              )}

              {!loading &&
                users.map((user) => (
                  <tr key={user.id}>
                    <td className="px-4 py-3 font-medium text-slate-900">{user.full_name}</td>
                    <td className="px-4 py-3 text-slate-600">{user.username}</td>
                    <td className="px-4 py-3 text-slate-600">
                      {ROLE_OPTIONS.find((option) => option.value === user.role)?.label}
                    </td>
                    <td className="px-4 py-3 text-slate-600">{user.venue_name || '—'}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  )
}
