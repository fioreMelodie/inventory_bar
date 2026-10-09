import api from './api'

/** Módulo 9 - Pagos y Facturación. */
export const billingService = {
  /**
   * Registra el pago de un pedido y devuelve la factura generada (HU23).
   * El monto recibido solo aplica al pago en efectivo.
   */
  async charge(orderId, { method, amountReceived }) {
    const payload = { payment_method: method }
    if (method === 'CASH') payload.amount_received = amountReceived

    const { data } = await api.post(`/orders/${orderId}/pay/`, payload)
    return data
  },
}

/** Métodos de pago aceptados, con su etiqueta en la interfaz. */
export const PAYMENT_METHODS = [{ value: 'CASH', label: 'Cash' }]
