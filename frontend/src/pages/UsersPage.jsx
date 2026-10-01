import { useEffect, useState } from 'react'
import ConfirmDialog from '../components/ConfirmDialog'
import { useAuth } from '../context/AuthContext'
import { getErrorMessage } from '../services/api'
import { ROLES_REQUIRING_VENUE, ROLE_OPTIONS, usersService } from '../services/users'
import { getFieldError, venuesService } from '../services/venues'

const EMPTY_FORM = {
  id: null,
  full_name: '',
  username: '',
  password: '',
  role: '',
  venue: '',
}

/**
 * HU06 - Crear usuario con rol y sede asignada.
 * HU07 - Editar usuario.
 * HU08 - Inactivar usuario.
 * Administración > Users. Acceso exclusivo del Administrador.
 */
export default function UsersPage() {
  const { user: currentUser } = useAuth()

  const [users, setUsers] = useState([])
  const [venues, setVenues] = useState([])
  const [loading, setLoading] = useState(true)
  const [includeInactive, setIncludeInactive] = useState(false)

  const [userToDeactivate, setUserToDeactivate] = useState(null)
  const [statusError, setStatusError] = useState('')
  const [changingStatus, setChangingStatus] = useState(false)

  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState(EMPTY_FORM)
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)
  const [feedback, setFeedback] = useState('')

  const venueRequired = ROLES_REQUIRING_VENUE.includes(form.role)
  const isEditing = form.id !== null

  useEffect(() => {
    loadData()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [includeInactive])

  /**
   * `showInactive` permite forzar el valor sin esperar a que React aplique el
   * cambio de estado, necesario justo después de inactivar una cuenta.
   */
  async function loadData(showInactive = includeInactive) {
    setLoading(true)
    try {
      const [userList, venueList] = await Promise.all([
        usersService.list({ includeInactive: showInactive }),
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

  function openCreateForm() {
    setForm(EMPTY_FORM)
    setFormError('')
    setFeedback('')
    setShowForm(true)
  }

  function openEditForm(user) {
    setForm({
      id: user.id,
      full_name: user.full_name,
      username: user.username,
      password: '',
      role: user.role,
      venue: user.venue ?? '',
    })
    setFormError('')
    setFeedback('')
    setShowForm(true)
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setFormError('')
    setFeedback('')

    const passwordMissing = !isEditing && !form.password
    if (!form.full_name.trim() || !form.username.trim() || passwordMissing || !form.role) {
      setFormError('Please complete all required fields.')
      return
    }

    if (venueRequired && !form.venue) {
      setFormError('Cashiers and waiters must be assigned to a venue.')
      return
    }

    const payload = {
      full_name: form.full_name.trim(),
      username: form.username.trim(),
      role: form.role,
      venue: form.venue || null,
    }
    // Al editar, la contraseña solo se envía si el Administrador la cambió.
    if (form.password) payload.password = form.password

    setSaving(true)
    try {
      if (isEditing) {
        await usersService.update(form.id, payload)
        setFeedback('User "' + payload.username + '" was updated successfully.')
      } else {
        await usersService.create(payload)
        setFeedback('User "' + payload.username + '" was created successfully.')
      }
      setShowForm(false)
      setForm(EMPTY_FORM)
      await loadData()
    } catch (requestError) {
      setFormError(
        getFieldError(requestError, 'username') ||
          getFieldError(requestError, 'password') ||
          getFieldError(requestError, 'venue') ||
          getFieldError(requestError, 'role') ||
          getErrorMessage(requestError, 'Unable to save the user.'),
      )
    } finally {
      setSaving(false)
    }
  }

  async function handleDeactivate() {
    setStatusError('')
    setChangingStatus(true)
    try {
      await usersService.deactivate(userToDeactivate.id)
      setFeedback(
        'User "' + userToDeactivate.username +
          '" is now inactive. The account is kept and can be reactivated.',
      )
      setUserToDeactivate(null)
      // La cuenta sigue existiendo: se muestran los inactivos para que la fila
      // no desaparezca y se vea su nuevo estado.
      setIncludeInactive(true)
      await loadData(true)
    } catch (requestError) {
      setStatusError(getErrorMessage(requestError, 'Unable to deactivate this user.'))
    } finally {
      setChangingStatus(false)
    }
  }

  async function handleActivate(user) {
    setFeedback('')
    try {
      await usersService.activate(user.id)
      setFeedback('User "' + user.username + '" was reactivated.')
      await loadData()
    } catch (requestError) {
      setFormError(getErrorMessage(requestError, 'Unable to reactivate this user.'))
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
          onClick={showForm ? () => setShowForm(false) : openCreateForm}
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
          <h2 className="text-base font-medium text-slate-900">
            {isEditing ? 'Edit user' : 'New user'}
          </h2>

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
                {isEditing ? 'New password' : 'Temporary password'}{' '}
                {isEditing ? (
                  <span className="text-slate-400">(leave blank to keep it)</span>
                ) : (
                  <span className="text-red-500">*</span>
                )}
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

      <label className="mt-6 flex items-center gap-2 text-sm text-slate-600">
        <input
          type="checkbox"
          checked={includeInactive}
          onChange={(event) => setIncludeInactive(event.target.checked)}
          className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
        />
        Show inactive users
      </label>

      <section className="mt-3 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
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
                  <td colSpan={6} className="px-4 py-6 text-center text-slate-500">
                    Loading users…
                  </td>
                </tr>
              )}

              {!loading && users.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-6 text-center text-slate-500">
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
                    <td className="px-4 py-3">
                      <span
                        className={
                          user.is_active
                            ? 'rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700'
                            : 'rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600'
                        }
                      >
                        {user.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex justify-end gap-2">
                        <button
                          type="button"
                          onClick={() => openEditForm(user)}
                          className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:bg-slate-50"
                        >
                          Edit
                        </button>

                        {user.is_active ? (
                          user.id !== currentUser.id && (
                            <button
                              type="button"
                              onClick={() => {
                                setStatusError('')
                                setUserToDeactivate(user)
                              }}
                              className="rounded-lg border border-red-200 px-3 py-1.5 text-xs font-medium text-red-700 transition hover:bg-red-50"
                            >
                              Deactivate
                            </button>
                          )
                        ) : (
                          <button
                            type="button"
                            onClick={() => handleActivate(user)}
                            className="rounded-lg border border-emerald-200 px-3 py-1.5 text-xs font-medium text-emerald-700 transition hover:bg-emerald-50"
                          >
                            Reactivate
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

      {userToDeactivate && (
        <ConfirmDialog
          title={'Deactivate "' + userToDeactivate.username + '"?'}
          message="The user will no longer be able to sign in and any active session will be
            closed immediately. Their activity history is kept, and open orders stay open so
            another user can handle them. You can reactivate the account later."
          confirmLabel="Deactivate"
          error={statusError}
          busy={changingStatus}
          onConfirm={handleDeactivate}
          onCancel={() => setUserToDeactivate(null)}
        />
      )}
    </main>
  )
}
