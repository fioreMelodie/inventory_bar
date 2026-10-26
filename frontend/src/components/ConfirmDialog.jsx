import { useEffect, useId, useRef } from 'react'
import { CircleAlert, LoaderCircle } from 'lucide-react'

export default function ConfirmDialog({
  title, message, confirmLabel = 'Confirm', cancelLabel = 'Cancel',
  error = '', busy = false, onConfirm, onCancel,
}) {
  const dialog = useRef(null)
  const titleId = useId()
  const descriptionId = useId()
  useEffect(() => { dialog.current?.showModal() }, [])
  function cancel() {
    if (busy) return
    dialog.current?.close()
    onCancel()
  }
  return (
    <dialog ref={dialog} className="confirmation-dialog" aria-labelledby={titleId} aria-describedby={descriptionId}
      onCancel={event => { event.preventDefault(); cancel() }}>
      <span className="dialog-symbol"><CircleAlert size={24} /></span>
      <h2 id={titleId}>{title}</h2>
      <p id={descriptionId}>{message}</p>
      {error && <p role="alert" className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
      <div className="dialog-actions">
        <button type="button" onClick={cancel} disabled={busy} autoFocus className="dialog-cancel">{cancelLabel}</button>
        <button type="button" onClick={onConfirm} disabled={busy} className="dialog-confirm">
          {busy && <LoaderCircle size={16} className="spin" />}{busy ? 'Working...' : confirmLabel}
        </button>
      </div>
    </dialog>
  )
}
