import api from './api'

/** Módulo 9 - Pagos y Facturación. */
export const billingService = {
  /**
   * Registra el pago de un pedido y devuelve la factura generada (HU23).
   * El monto recibido solo aplica al pago en efectivo.
   */
  async charge(orderId, { method, amountReceived, cardApproved }) {
    const payload = { payment_method: method }

    if (method === 'CASH') {
      payload.amount_received = amountReceived
    } else {
      // El cobro se hizo en el datáfono externo; el cajero confirma que fue
      // aprobado (HU24).
      payload.card_approved = Boolean(cardApproved)
    }

    const { data } = await api.post(`/orders/${orderId}/pay/`, payload)
    return data
  },
}

/** Métodos de pago aceptados, con su etiqueta en la interfaz. */
export const PAYMENT_METHODS = [
  { value: 'CASH', label: 'Cash' },
  { value: 'CREDIT_CARD', label: 'Credit card' },
  { value: 'DEBIT_CARD', label: 'Debit card' },
]

/** Métodos que se cobran en el datáfono externo. */
export const CARD_METHODS = ['CREDIT_CARD', 'DEBIT_CARD']
