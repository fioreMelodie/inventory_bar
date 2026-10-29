import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getErrorMessage } from '../services/api'
import { billingService } from '../services/billing'
import { formatPrice } from '../services/products'

/**
 * HU25 - Consulta e impresión de la factura.
 *
 * La factura se genera sola al completar el pago; esta pantalla solo la
 * presenta. Es de solo lectura: no hay forma de editarla ni anularla.
 */
export default function InvoicePage() {
  const { invoiceId } = useParams()

  const [invoice, setInvoice] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    loadInvoice()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [invoiceId])

  async function loadInvoice() {
    setLoading(true)
    try {
      setInvoice(await billingService.retrieve(invoiceId))
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Unable to load this invoice.'))
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <main className="mx-auto max-w-2xl px-4 py-8">
        <p className="text-sm text-slate-500">Loading invoice…</p>
      </main>
    )
  }

  if (!invoice) {
    return (
      <main className="mx-auto max-w-2xl px-4 py-8">
        <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error || 'Invoice not found.'}
        </p>
      </main>
    )
  }

  return (
    <main className="mx-auto max-w-2xl px-4 py-8">
      {/* Estos controles no deben salir en el papel. */}
      <div className="flex items-center justify-between print:hidden">
        <Link to="/billing" className="text-sm text-brand-700 underline">
          Back to invoices
        </Link>

        <button
          type="button"
          onClick={() => window.print()}
          className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
        >
          Print
        </button>
      </div>

      <article className="mt-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm print:border-0 print:shadow-none">
        <header className="border-b border-slate-200 pb-4 text-center">
          <h1 className="text-lg font-semibold text-slate-900">Cafe Colombia Bar</h1>
          <p className="text-sm text-slate-500">{invoice.venue_name}</p>
          <p className="mt-2 text-base font-medium text-slate-900">
            Invoice {invoice.number}
          </p>
          <p className="text-xs text-slate-500">
            {new Date(invoice.created_at).toLocaleString('en-US')}
          </p>
        </header>

        <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
          <dt className="text-slate-500">Table</dt>
          <dd className="text-right text-slate-900">{invoice.table_identifier}</dd>

          <dt className="text-slate-500">Waiter</dt>
          <dd className="text-right text-slate-900">{invoice.waiter_name}</dd>

          <dt className="text-slate-500">Cashier</dt>
          <dd className="text-right text-slate-900">{invoice.cashier_name}</dd>

          <dt className="text-slate-500">Payment method</dt>
          <dd className="text-right text-slate-900">{invoice.payment_method_label}</dd>
        </dl>

        <table className="mt-6 w-full text-left text-sm">
          <thead className="border-y border-slate-200 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th scope="col" className="py-2 font-medium">
                Product
              </th>
              <th scope="col" className="py-2 text-right font-medium">
                Qty
              </th>
              <th scope="col" className="py-2 text-right font-medium">
                Unit
              </th>
              <th scope="col" className="py-2 text-right font-medium">
                Subtotal
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {invoice.items.map((item) => (
              <tr key={item.id}>
                <td className="py-2 text-slate-900">{item.product_name}</td>
                <td className="py-2 text-right text-slate-600">{item.quantity}</td>
                <td className="py-2 text-right text-slate-600">
                  {formatPrice(item.unit_price)}
                </td>
                <td className="py-2 text-right font-medium text-slate-900">
                  {formatPrice(item.subtotal)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        <div className="mt-4 border-t border-slate-200 pt-4 text-sm">
          <div className="flex items-center justify-between">
            <span className="font-medium text-slate-900">Total</span>
            <span className="text-lg font-semibold text-slate-900">
              {formatPrice(invoice.total)}
            </span>
          </div>

          {invoice.amount_received !== null && (
            <>
              <div className="mt-2 flex items-center justify-between text-slate-600">
                <span>Amount received</span>
                <span>{formatPrice(invoice.amount_received)}</span>
              </div>
              <div className="flex items-center justify-between text-slate-600">
                <span>Change</span>
                <span>{formatPrice(invoice.change_given)}</span>
              </div>
            </>
          )}
        </div>

        <footer className="mt-6 border-t border-slate-200 pt-4 text-center text-xs text-slate-500">
          Thank you for your visit.
        </footer>
      </article>
    </main>
  )
}
