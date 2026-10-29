import { useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { ArrowLeft, Check, Printer } from 'lucide-react'
import { paymentsService } from '../services/payments'
import { getErrorMessage } from '../services/api'
import { formatPrice } from '../services/products'

export default function InvoicePage() {
  const { invoiceId } = useParams()
  const { state } = useLocation()
  const fromReceipts = state?.from === '/invoices'
  const [invoice, setInvoice] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')
    setInvoice(null)
    paymentsService.receipt(invoiceId).then(data => {
      if (!cancelled) setInvoice(data)
    }).catch(requestError => {
      if (!cancelled) setError(getErrorMessage(requestError, 'Unable to load the receipt.'))
    }).finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [invoiceId])
  const data = invoice?.snapshot
  const methodLabel = { CASH: 'Cash', CREDIT_CARD: 'Credit card', DEBIT_CARD: 'Debit card' }[data?.method] || data?.method
  return (
    <main className="receipt-page">
      <div className="receipt-navigation">
        <Link to={fromReceipts ? '/invoices' + (state.search || '') : '/cashier/pending'} className="text-link"><ArrowLeft size={16} />{fromReceipts ? 'Back to receipts' : 'Back to pending orders'}</Link>
        {invoice && <button className="icon-button refresh-button" onClick={() => window.print()} aria-label="Print receipt" title="Print receipt"><Printer size={18} /></button>}
      </div>
      {loading && <p className="table-note">Loading receipt...</p>}
      {error && <p role="alert" className="error-banner">{error}</p>}
      {invoice && <article className="payment-receipt" aria-label="Payment receipt">
        <header className="receipt-heading">
          <div><p className="eyebrow">Cafe Colombia Bar</p><h1>Payment receipt</h1><p className="receipt-number">{invoice.number}</p></div>
          <span className="status-pill green"><Check size={12} /> Paid</span>
        </header>
        <dl className="receipt-metadata">
          <div><dt>Venue</dt><dd>{data.venue_name}</dd></div>
          <div><dt>Date</dt><dd>{new Date(invoice.issued_at).toLocaleString('en-US', { timeZone: 'America/Bogota' })}</dd></div>
          <div><dt>Order / Table</dt><dd>#{data.order_id} · {data.table_identifier}</dd></div>
          <div><dt>Method</dt><dd>{methodLabel}</dd></div>
          {data.approval_reference && <div><dt>Approval reference</dt><dd>{data.approval_reference}</dd></div>}
          <div><dt>Waiter</dt><dd>{data.waiter_name}</dd></div>
          <div><dt>Cashier</dt><dd>{data.cashier_name}</dd></div>
        </dl>
        <div className="receipt-items-wrap"><table className="receipt-items">
          <thead><tr><th>Product</th><th>Qty</th><th>Unit price</th><th>Subtotal</th></tr></thead>
          <tbody>{data.items.map((item, index) => <tr key={index}><td>{item.product_name}</td><td>{item.quantity}</td><td>{formatPrice(item.unit_price)}</td><td>{formatPrice(item.subtotal)}</td></tr>)}</tbody>
        </table></div>
        <dl className="receipt-totals">
          <div><dt>Total paid</dt><dd>{formatPrice(data.total)}</dd></div>
          {data.method === 'CASH' && <><div><dt>Amount received</dt><dd>{formatPrice(data.received_amount)}</dd></div>
          <div><dt>Change</dt><dd>{formatPrice(data.change)}</dd></div></>}
        </dl>
        <footer className="receipt-footnote">Internal payment receipt · COP</footer>
      </article>}
    </main>
  )
}
