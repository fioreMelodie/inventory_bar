import { useAuth } from '../context/AuthContext'

/**
 * Menú principal al que se redirige tras iniciar sesión.
 * Las opciones de cada rol se incorporan en las historias siguientes.
 */
export default function HomePage() {
  const { user } = useAuth()

  return (
    <main className="mx-auto max-w-4xl px-4 py-10">
      <header className="border-b border-slate-200 pb-6">
        <h1 className="text-xl font-semibold text-slate-900">
          Welcome, {user.full_name.split(' ')[0]}
        </h1>
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
