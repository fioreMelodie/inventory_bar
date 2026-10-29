import { useEffect, useState } from 'react'
import { ArrowRight, Coffee, Eye, EyeOff, LoaderCircle } from 'lucide-react'
import { Navigate, useNavigate } from 'react-router-dom'
import { HOME_ROUTE_BY_ROLE, useAuth } from '../context/AuthContext'
import { getErrorMessage } from '../services/api'

/**
 * HU01 - Inicio de sesión con credenciales.
 * Todo el texto visible está en inglés (requisito no funcional).
 */
export default function LoginPage() {
  const { login, isAuthenticated, user, sessionNotice, setSessionNotice } = useAuth()
  const navigate = useNavigate()

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [retryAfter, setRetryAfter] = useState(0)
  const [submitting, setSubmitting] = useState(false)
  const [showPassword, setShowPassword] = useState(false)

  // Cuenta regresiva del bloqueo por intentos fallidos.
  useEffect(() => {
    if (retryAfter <= 0) return undefined
    const timer = setInterval(() => setRetryAfter((seconds) => Math.max(0, seconds - 1)), 1000)
    return () => clearInterval(timer)
  }, [retryAfter])

  if (isAuthenticated) {
    return <Navigate to={HOME_ROUTE_BY_ROLE[user.role] || '/login'} replace />
  }

  const isLocked = retryAfter > 0

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')

    if (!username.trim() || !password) {
      setError('Please enter your username and password.')
      return
    }

    setSessionNotice('')
    setSubmitting(true)
    try {
      const authenticatedUser = await login(username.trim(), password)
      navigate(HOME_ROUTE_BY_ROLE[authenticatedUser.role] || '/login', { replace: true })
    } catch (requestError) {
      const seconds = requestError?.response?.data?.retry_after_seconds
      if (seconds) setRetryAfter(seconds)
      setError(getErrorMessage(requestError, 'Unable to sign in. Please try again.'))
      setPassword('')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="login-screen">
      <div className="login-panel">
        <div className="brand-lockup">
          <span className="brand-mark"><Coffee size={23} /></span>
          <span><strong>Bar Inventory</strong><small>Cafe Colombia Bar</small></span>
        </div>

        <form
          onSubmit={handleSubmit}
          noValidate
          className="login-form"
        >
          <h1>Sign in</h1>

          <div className="mt-6">
            <label htmlFor="username" className="block text-sm font-medium text-slate-700">
              Username
            </label>
            <input
              id="username"
              name="username"
              type="text"
              autoComplete="username"
              autoFocus
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              disabled={isLocked || submitting}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100 disabled:bg-slate-50"
            />
          </div>

          <div className="mt-4">
            <label htmlFor="password" className="block text-sm font-medium text-slate-700">
              Password
            </label>
            <div className="password-field"><input
              id="password"
              name="password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              disabled={isLocked || submitting}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100 disabled:bg-slate-50"
            />
            <button type="button" className="icon-button" onClick={() => setShowPassword(value => !value)} aria-label={showPassword ? 'Hide password' : 'Show password'} title={showPassword ? 'Hide password' : 'Show password'} aria-pressed={showPassword} disabled={isLocked || submitting}>
              {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
            </button></div>
          </div>

          {sessionNotice && !error && (
            <p role="status" className="mt-4 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">
              {sessionNotice}
            </p>
          )}

          {error && (
            <p role="alert" className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </p>
          )}

          {isLocked && (
            <p className="mt-2 text-center text-xs text-slate-500">
              You can try again in {retryAfter} second{retryAfter === 1 ? '' : 's'}.
            </p>
          )}

          <button
            type="submit"
            disabled={isLocked || submitting}
            className="mt-6 w-full rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            {submitting ? <LoaderCircle size={17} className="spin" /> : null}
            {submitting ? 'Signing in…' : 'Sign in'}
            {!submitting && <ArrowRight size={17} />}
          </button>

        </form>
        <span className="login-caption">Cafe Colombia Bar · Staff access</span>
      </div>
    </main>
  )
}
