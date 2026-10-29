import { useEffect, useRef, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { ArrowUpRight, BarChart3, BookOpen, Boxes, Building2, ChevronRight, Coffee, LayoutDashboard, LogOut, Menu, ReceiptText, ShieldCheck, Table2, Truck, Users, Wifi, WifiOff, X } from 'lucide-react'
import { ROLE_LABELS, useAuth } from '../context/AuthContext'
import useConnectionStatus from '../hooks/useConnectionStatus'
import ConnectionLostDialog from './ConnectionLostDialog'

const ITEMS = [
  { to: '/audit/events', label: 'Event log', icon: ShieldCheck, group: 'Audit', roles: ['ADMIN'] },
  { to: '/reports/my-sales', label: 'Sales report', icon: BarChart3, group: 'Reports', roles: ['CASHIER'] },
  { to: '/reports/sales', label: 'Sales report', icon: BarChart3, group: 'Reports', roles: ['ADMIN'] },
  { to: '/cashier/pending', label: 'Pending orders', icon: ReceiptText, group: 'Operations', roles: ['ADMIN', 'CASHIER'] },
  { to: '/invoices', label: 'Receipts', icon: ReceiptText, group: 'Operations', roles: ['ADMIN', 'CASHIER'] },
  { to: '/room', label: 'Room', icon: Table2, group: 'Operations' },
  { to: '/catalog', label: 'Catalog', icon: BookOpen, group: 'Operations' },
  { to: '/inventory', label: 'Inventory', icon: Boxes, group: 'Operations', roles: ['ADMIN', 'CASHIER'] },
  { to: '/admin/venues', label: 'Venues', icon: Building2, group: 'Management', roles: ['ADMIN'] },
  { to: '/admin/users', label: 'Users', icon: Users, group: 'Management', roles: ['ADMIN'] },
  { to: '/admin/suppliers', label: 'Suppliers', icon: Truck, group: 'Management', roles: ['ADMIN'] },
  { to: '/admin/tables', label: 'Tables', icon: Table2, group: 'Management', roles: ['ADMIN'] },
]
const HOME = { ADMIN: '/admin', CASHIER: '/cashier', WAITER: '/waiter' }

function Navigation({ user, onNavigate, onSignOut }) {
  return (
    <div className="sidebar-inner">
      <NavLink to={HOME[user.role]} className="brand-lockup" onClick={onNavigate}>
        <span className="brand-mark"><Coffee size={22} strokeWidth={1.7} /></span>
        <span><strong>Bar Inventory</strong><small>Cafe Colombia Bar</small></span>
      </NavLink>
      <nav aria-label="Main navigation">
        <NavLink to={HOME[user.role]} end onClick={onNavigate} className={({ isActive }) => 'nav-item ' + (isActive ? 'active' : '')}>
          <LayoutDashboard size={19} /> Overview
        </NavLink>
        {['Operations', 'Management', 'Reports', 'Audit'].map(group => {
          const items = ITEMS.filter(item => item.group === group && (!item.roles || item.roles.includes(user.role)))
          return items.length > 0 && <div key={group} className="nav-group">
            <p className="nav-label">{group}</p>
            {items.map(({ icon: Icon, ...item }) => <NavLink key={item.to} to={item.to} onClick={onNavigate} className={({ isActive }) => 'nav-item ' + (isActive ? 'active' : '')}>
              <Icon size={19} strokeWidth={1.7} /> {item.label}
            </NavLink>)}
          </div>
        })}
      </nav>
      <div className="sidebar-bottom">
        <NavLink to="/room" onClick={onNavigate} className="room-shortcut"><Table2 size={18} /> Open room <ArrowUpRight size={16} /></NavLink>
        <div className="profile-row">
          <span className="avatar">{user.full_name.slice(0, 1).toUpperCase()}</span>
          <span className="profile-name"><strong>{user.full_name}</strong><small>{ROLE_LABELS[user.role]}</small></span>
          <button className="icon-button" title="Sign out" aria-label="Sign out" onClick={onSignOut}><LogOut size={18} /></button>
        </div>
      </div>
    </div>
  )
}

export default function AppLayout({ children }) {
  const { user, signOut, reportConnectionLoss } = useAuth()
  const isOnline = useConnectionStatus()
  const [connectionLost, setConnectionLost] = useState(!isOnline)
  const mobileMenu = useRef(null)
  const location = useLocation()
  const current = ITEMS.find(item => item.to === location.pathname)?.label || (location.pathname.startsWith('/orders/') ? 'Order details' : location.pathname.startsWith('/invoices/') ? 'Payment receipt' : 'Overview')
  useEffect(() => { if (!isOnline) setConnectionLost(true) }, [isOnline])
  const closeMenu = () => mobileMenu.current?.close()

  return (
    <div className="app-shell">
      <a href="#main-content" className="skip-link">Skip to content</a>
      <aside className="desktop-sidebar"><Navigation user={user} onSignOut={signOut} /></aside>
      <dialog ref={mobileMenu} className="mobile-navigation" aria-label="Navigation menu" onClick={event => { if (event.target === event.currentTarget) closeMenu() }}>
        <button onClick={closeMenu} className="icon-button mobile-close" aria-label="Close navigation" title="Close navigation"><X size={20} /></button>
        <Navigation user={user} onNavigate={closeMenu} onSignOut={() => { closeMenu(); signOut() }} />
      </dialog>
      <div className="workspace">
        <header className="workspace-topbar">
          <div className="breadcrumb">
            <button className="icon-button menu-toggle" onClick={() => mobileMenu.current?.showModal()} aria-label="Open navigation" title="Open navigation"><Menu size={21} /></button>
            <span className="breadcrumb-root">Workspace</span><ChevronRight size={14} /><span>{current}</span>
          </div>
          <div className="topbar-meta">
            <span className="topbar-date">{new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric' }).format(new Date())}</span>
            <span className={'connection-state ' + (!isOnline ? 'offline' : '')}>{isOnline ? <Wifi size={14} /> : <WifiOff size={14} />}{isOnline ? 'Connected' : 'Offline'}</span>
          </div>
        </header>
        <div id="main-content" tabIndex={-1}>{children}</div>
        <footer className="workspace-footer"><span>Cafe Colombia Bar</span><span>Bar Inventory</span></footer>
      </div>
      {connectionLost && <ConnectionLostDialog onConfirm={reportConnectionLoss} />}
    </div>
  )
}
