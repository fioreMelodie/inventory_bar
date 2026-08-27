/**
 * HU03 - Aviso de pérdida de conexión.
 *
 * El mensaje no desaparece hasta que el usuario lo confirma explícitamente:
 * el diálogo es modal y no se cierra al hacer clic fuera ni con la tecla Esc.
 */
export default function ConnectionLostDialog({ onConfirm }) {
  return (
    <div
      role="alertdialog"
      aria-modal="true"
      aria-labelledby="connection-lost-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 px-4"
    >
      <div className="w-full max-w-sm rounded-xl bg-white p-6 shadow-xl">
        <h2 id="connection-lost-title" className="text-base font-semibold text-slate-900">
          Connection lost
        </h2>
        <p className="mt-2 text-sm text-slate-600">
          Your internet connection is unavailable. Your order has been saved and no data was
          lost. You will be signed out and can continue once the connection is restored.
        </p>
        <button
          type="button"
          onClick={onConfirm}
          autoFocus
          className="mt-6 w-full rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
        >
          Understood
        </button>
      </div>
    </div>
  )
}
