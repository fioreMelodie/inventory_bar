import { NavLink } from 'react-router-dom'
import { ROLE_LABELS, useAuth } from '../context/AuthContext'
import useConnectionStatus from '../hooks/useConnectionStatus'
import ConnectionLostDialog from './ConnectionLostDialog'

/** Opciones de menú disponibles para cada rol. */
const MENU_BY_ROLE = {
  ADMIN: [
    { to: '/admin', label: 'Home', end: true },
    { to: '/admin/venues', label: 'Venues' },
    { to: '/admin/users', label: 'Users' },
    { to: '/catalog', label: 'Catalog' },
    { to: '/admin/suppliers', label: 'Suppliers' },
  ],
  CASHIER: [
    { to: '/cashier', label: 'Home', end: true },
    { to: '/catalog', label: 'Catalog' },
  ],
  WAITER: [
    { to: '/waiter', label: 'Home', end: true },
    { to: '/catalog', label: 'Catalog' },
  ],
}

/**
 * Marco común de las pantallas autenticadas.
 *
 * HU03: el botón de cierre de sesión está visible en todo momento desde el
 * menú principal, y la pérdida de conexión muestra un aviso que exige
 * confirmación del usuario.
 */
export default function AppLayout({ children }) {
  const { user, signOut, reportConnectionLoss } = useAuth()
  const isOnline = useConnectionStatus()
  const menu = MENU_BY_ROLE[user.role] ?? []

  return (
    <div className="min-h-full">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-3 px-4 py-3">
          <div>
            <p className="text-sm font-semibold text-slate-900">Bar Inventory</p>
            <p className="text-xs text-slate-500">
              {user.full_name} · {ROLE_LABELS[user.role]}
            </p>
          </div>

          <nav className="order-last w-full sm:order-none sm:w-auto">
            <ul className="flex gap-1">
              {menu.map((item) => (
                <li key={item.to}>
                  <NavLink
                    to={item.to}
                    end={item.end}
                    className={({ isActive }) =>
                      [
                        'block rounded-lg px-3 py-1.5 text-sm font-medium transition',
                        isActive
                          ? 'bg-brand-50 text-brand-700'
                          : 'text-slate-600 hover:bg-slate-50',
                      ].join(' ')
                    }
                  >
                    {item.label}
                  </NavLink>
                </li>
              ))}
            </ul>
          </nav>

          <button
            type="button"
            onClick={signOut}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
          >
            Sign out
          </button>
        </div>
      </header>

      {children}

      {!isOnline && <ConnectionLostDialog onConfirm={reportConnectionLoss} />}
    </div>
  )
}
