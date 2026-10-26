import { useEffect, useId, useRef, useState } from 'react'
import { Banknote, LoaderCircle } from 'lucide-react'
import { getErrorMessage } from '../services/api'
import { paymentsService } from '../services/payments'
import { formatPrice } from '../services/products'

export default function CashPaymentDialog({ order, onCancel, onPaid, onReload }) {
  const dialog = useRef(null)
  const busyRef = useRef(false)
  const attempt = useRef(null)
  const titleId = useId()
  const inputId = useId()
  const errorId = useId()
  const [received, setReceived] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [conflict, setConflict] = useState(false)
  const amount = Number(received)
  const valid = received.trim() !== '' && Number.isSafeInteger(amount) && amount >= order.total && amount <= 2147483647

  useEffect(() => { dialog.current?.showModal() }, [])
  function cancel() {
    if (busyRef.current) return
    dialog.current?.close()
    onCancel()
  }
  async function submit(event) {
    event.preventDefault()
    if (busyRef.current) return
    if (!valid) {
      setError('Enter a whole amount that covers the order total.')
      return
    }
    busyRef.current = true
    setBusy(true)
    setError('')
    setConflict(false)
    const storageKey = 'bar_inventory_cash_payment_' + order.id
    try {
      // Se conserva la referencia si se pierde la respuesta o se recarga la pagina.
      if (!attempt.current || attempt.current.received_amount !== amount) {
        let saved
        try { saved = JSON.parse(sessionStorage.getItem(storageKey)) } catch { saved = null }
        attempt.current = saved?.received_amount === amount && saved?.expected_total === order.total
          ? saved
          : { idempotency_key: crypto.randomUUID(), received_amount: amount, expected_total: order.total }
      }
      try { sessionStorage.setItem(storageKey, JSON.stringify(attempt.current)) } catch { /* La referencia sigue en memoria. */ }
      const result = await paymentsService.cash({ order: order.id, ...attempt.current })
      try { sessionStorage.removeItem(storageKey) } catch { /* No afecta el pago registrado. */ }
      dialog.current?.close()
      onPaid(result.invoice)
    } catch (requestError) {
      const field = requestError?.response?.data?.received_amount
      setError((Array.isArray(field) ? field[0] : field) || getErrorMessage(requestError, 'Unable to confirm payment. Retry with the same amount or reload the order.'))
      setConflict(requestError?.response?.status === 409)
    } finally {
      busyRef.current = false
      setBusy(false)
    }
  }
  return (
    <dialog ref={dialog} className="confirmation-dialog cash-dialog" aria-labelledby={titleId}
      onCancel={event => { event.preventDefault(); cancel() }}>
      <span className="dialog-symbol cash-symbol"><Banknote size={25} /></span>
      <h2 id={titleId}>Cash payment</h2>
      <p>Order #{order.id} · {order.table_identifier}</p>
      <form onSubmit={submit} noValidate>
        <dl className="cash-breakdown"><div><dt>Order total</dt><dd>{formatPrice(order.total)}</dd></div></dl>
        <label htmlFor={inputId}>Amount received (COP)</label>
        <input id={inputId} type="number" inputMode="numeric" min={order.total} max="2147483647" step="1"
          value={received} onChange={event => { setReceived(event.target.value); setError(''); setConflict(false) }}
          autoFocus disabled={busy} aria-invalid={!!error} aria-describedby={error ? errorId : undefined} />
        <dl className="cash-breakdown"><div><dt>Change</dt><dd aria-live="polite">{valid ? formatPrice(amount - order.total) : '--'}</dd></div></dl>
        {error && <p id={errorId} role="alert" className="cash-error">{error}</p>}
        {conflict && <button type="button" className="text-link mt-3" onClick={() => { dialog.current?.close(); onReload() }}>Reload order</button>}
        <div className="dialog-actions">
          <button type="button" className="dialog-cancel" onClick={cancel} disabled={busy}>Cancel</button>
          <button type="submit" className="cash-confirm" disabled={busy || conflict}>{busy && <LoaderCircle size={16} className="spin" />}{busy ? 'Confirming...' : 'Confirm cash payment'}</button>
        </div>
      </form>
    </dialog>
  )
}
