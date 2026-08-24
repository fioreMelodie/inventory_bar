import { Route, Routes } from 'react-router-dom'

/**
 * Raíz de la aplicación.
 * Las rutas de cada módulo se incorporan a medida que avanzan las historias
 * de usuario. Todo el texto visible está en inglés.
 */
export default function App() {
  return (
    <Routes>
      <Route
        path="*"
        element={
          <main className="flex h-full items-center justify-center p-6">
            <div className="text-center">
              <h1 className="text-2xl font-semibold text-slate-900">Bar Inventory</h1>
              <p className="mt-2 text-sm text-slate-500">Cafe Colombia Bar</p>
            </div>
          </main>
        }
      />
    </Routes>
  )
}
