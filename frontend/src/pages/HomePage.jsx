import { ROLE_LABELS, useAuth } from '../context/AuthContext'

/**
 * Menú principal al que se redirige tras iniciar sesión.
 * Las opciones de cada rol se incorporan en las historias siguientes.
 */
export default function HomePage() {
  const { user } = useAuth()

  return (
    <main className="mx-auto max-w-4xl px-4 py-10">
      <header className="border-b border-slate-200 pb-6">
        <p className="text-sm text-slate-500">Signed in as</p>
        <h1 className="mt-1 text-xl font-semibold text-slate-900">{user.full_name}</h1>
        <span className="mt-2 inline-block rounded-full bg-brand-50 px-3 py-1 text-xs font-medium text-brand-700">
          {ROLE_LABELS[user.role]}
        </span>
      </header>

      <section className="mt-8">
        <h2 className="text-sm font-medium text-slate-900">Main menu</h2>
        <p className="mt-2 text-sm text-slate-500">
          The options available for your role will appear here.
        </p>
      </section>
    </main>
  )
}
