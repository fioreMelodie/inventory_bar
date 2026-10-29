import { useEffect, useId, useRef, useState } from 'react'
import { CreditCard, LoaderCircle } from 'lucide-react'
import { getErrorMessage } from '../services/api'
import { paymentsService } from '../services/payments'
import { formatPrice } from '../services/products'

export default function CardPaymentDialog({ order, onCancel, onPaid, onReload }) {
  const dialog = useRef(null)
  const referenceInput = useRef(null)
  const busyRef = useRef(false)
  const attempt = useRef(null)
  const titleId = useId()
  const referenceId = useId()
  const errorId = useId()
  const groupId = useId()
  const [method, setMethod] = useState('CREDIT_CARD')
  const [reference, setReference] = useState('')
  const [approved, setApproved] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [conflict, setConflict] = useState(false)

  useEffect(() => {
    dialog.current?.showModal()
    referenceInput.current?.focus()
  }, [])
  function clearError() { setError(''); setConflict(false) }
  function cancel() {
    if (busyRef.current) return
    dialog.current?.close()
    onCancel()
  }
  async function submit(event) {
    event.preventDefault()
    if (busyRef.current) return
    const normalized = reference.trim().toUpperCase()
    if (!/^[A-Z0-9][A-Z0-9._/-]{2,39}$/.test(normalized)) {
      setError('Enter a terminal approval reference of 3 to 40 letters or numbers, with dots, hyphens, underscores or slashes.')
      return
    }
    if (/\d(?:[._/-]*\d){12,}/.test(normalized)) {
      setError('Do not enter a card number. Use the terminal approval reference.')
      return
    }
    if (!approved) {
      setError('Confirm that the payment was approved on the external terminal.')
      return
    }
    busyRef.current = true
    setBusy(true)
    clearError()
    const storageKey = 'bar_inventory_card_payment_' + order.id
    try {
      const matches = value => value?.method === method && value?.approval_reference === normalized &&
        value?.expected_total === order.total && typeof value?.idempotency_key === 'string'
      if (!matches(attempt.current)) {
        let saved
        try { saved = JSON.parse(sessionStorage.getItem(storageKey)) } catch { saved = null }
        attempt.current = {
          method, approval_reference: normalized, expected_total: order.total,
          idempotency_key: matches(saved) ? saved.idempotency_key : crypto.randomUUID(),
        }
      }
      try { sessionStorage.setItem(storageKey, JSON.stringify(attempt.current)) } catch { /* La referencia sigue en memoria. */ }
      const result = await paymentsService.card({ order: order.id, ...attempt.current, terminal_approved: true })
      try { sessionStorage.removeItem(storageKey) } catch { /* No afecta el pago registrado. */ }
      dialog.current?.close()
      onPaid(result.invoice)
    } catch (requestError) {
      const data = requestError?.response?.data
      const field = data?.approval_reference || data?.terminal_approved || data?.method
      setError((Array.isArray(field) ? field[0] : field) || getErrorMessage(requestError, 'Unable to record payment. Retry with the same details or reload the order.'))
      setConflict(requestError?.response?.status === 409)
    } finally {
      busyRef.current = false
      setBusy(false)
    }
  }
  return (
    <dialog ref={dialog} className="confirmation-dialog card-dialog" aria-labelledby={titleId}
      onCancel={event => { event.preventDefault(); cancel() }}>
      <span className="dialog-symbol card-symbol"><CreditCard size={25} /></span>
      <h2 id={titleId}>Card payment</h2>
      <p>Order #{order.id} · {order.table_identifier}</p>
      <form onSubmit={submit} noValidate>
        <dl className="cash-breakdown"><div><dt>Total to record</dt><dd>{formatPrice(order.total)}</dd></div></dl>
        <fieldset className="card-methods" disabled={busy}>
          <legend>Card type</legend>
          <div className="card-method-options">
            {[['CREDIT_CARD', 'Credit card'], ['DEBIT_CARD', 'Debit card']].map(([value, label]) =>
              <label key={value}><input type="radio" name={groupId} value={value} checked={method === value}
                onChange={() => { setMethod(value); setApproved(false); clearError() }} /><span>{label}</span></label>)}
          </div>
        </fieldset>
        <label htmlFor={referenceId}>Approval reference</label>
        <input ref={referenceInput} id={referenceId} className="card-reference" type="text" autoComplete="off" spellCheck={false} maxLength={40}
          value={reference} onChange={event => { setReference(event.target.value); setApproved(false); clearError() }}
          autoFocus disabled={busy} aria-invalid={!!error} aria-describedby={error ? errorId : undefined} />
        <label className="terminal-confirmation"><input type="checkbox" checked={approved}
          onChange={event => { setApproved(event.target.checked); clearError() }} disabled={busy} />
          <span>I confirm the payment was approved on the external terminal.</span></label>
        {error && <p id={errorId} role="alert" className="cash-error">{error}</p>}
        {conflict && <button type="button" className="text-link mt-3" onClick={() => { dialog.current?.close(); onReload() }}>Reload order</button>}
        <div className="dialog-actions">
          <button type="button" className="dialog-cancel" onClick={cancel} disabled={busy}>Cancel</button>
          <button type="submit" className="cash-confirm" disabled={busy || conflict}>{busy && <LoaderCircle size={16} className="spin" />}{busy ? 'Confirming...' : 'Confirm card payment'}</button>
        </div>
      </form>
    </dialog>
  )
}
