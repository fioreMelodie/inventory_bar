import { useState } from 'react'
import { getErrorMessage } from '../services/api'
import { billingService, PAYMENT_METHODS } from '../services/billing'
import { formatPrice } from '../services/products'

/**
 * HU23 - Cobro de un pedido.
 *
 * El cambio se calcula en pantalla mientras el cajero escribe, pero el valor
 * que queda en la factura lo calcula el servidor.
 */
export default function PaymentDialog({ order, onPaid, onCancel }) {
  const [method, setMethod] = useState(PAYMENT_METHODS[0].value)
  const [amountReceived, setAmountReceived] = useState('')
  const [error, setError] = useState('')
  const [charging, setCharging] = useState(false)

  const isCash = method === 'CASH'
  const received = Number(amountReceived)
  const change = isCash && received >= order.total ? received - order.total : null

  async function handleCharge() {
    setError('')

    if (isCash) {
      if (!amountReceived || !Number.isInteger(received) || received < 0) {
        setError('Enter the amount received from the customer.')
        return
      }
      if (received < order.total) {
        setError('The amount received is lower than the order total.')
        return
      }
    }

    setCharging(true)
    try {
      const invoice = await billingService.charge(order.id, {
        method,
        amountReceived: received,
      })
      onPaid(invoice)
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Unable to register the payment.'))
    } finally {
      setCharging(false)
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="payment-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 px-4"
    >
      <div className="w-full max-w-sm rounded-xl bg-white p-6 shadow-xl">
        <h2 id="payment-title" className="text-base font-semibold text-slate-900">
          Charge order #{order.id}
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          {order.table_identifier} · {order.waiter_name}
        </p>

        <div className="mt-4 rounded-lg bg-slate-50 px-4 py-3">
          <p className="text-xs uppercase tracking-wide text-slate-500">Total to pay</p>
          <p className="text-2xl font-semibold text-slate-900">{formatPrice(order.total)}</p>
        </div>

        <div className="mt-4">
          <label htmlFor="method" className="block text-sm font-medium text-slate-700">
            Payment method
          </label>
          <select
            id="method"
            value={method}
            onChange={(event) => setMethod(event.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
          >
            {PAYMENT_METHODS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        {isCash && (
          <div className="mt-4">
            <label
              htmlFor="amount-received"
              className="block text-sm font-medium text-slate-700"
            >
              Amount received <span className="text-red-500">*</span>
            </label>
            <input
              id="amount-received"
              type="number"
              min="0"
              step="1"
              value={amountReceived}
              onChange={(event) => setAmountReceived(event.target.value)}
              autoFocus
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            />

            {change !== null && (
              <p className="mt-2 rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
                Change: <span className="font-semibold">{formatPrice(change)}</span>
              </p>
            )}
          </div>
        )}

        {error && (
          <p role="alert" className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}

        <div className="mt-6 flex justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            disabled={charging}
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleCharge}
            disabled={charging}
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-brand-700 disabled:bg-slate-300"
          >
            {charging ? 'Charging…' : 'Confirm payment'}
          </button>
        </div>
      </div>
    </div>
  )
}
