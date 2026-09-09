import api from './api'

/** Módulo 4 - Catálogo de Productos. */
export const productsService = {
  /** Lista los productos del catálogo. */
  async list({ includeInactive = false } = {}) {
    const { data } = await api.get('/products/', {
      params: includeInactive ? { include_inactive: 'true' } : undefined,
    })
    return data.results ?? data
  },

  /**
   * Crea un producto (HU09).
   * Si se adjunta imagen se envía como multipart; si no, como JSON.
   */
  async create(product, image) {
    if (!image) {
      const { data } = await api.post('/products/', product)
      return data
    }

    const payload = new FormData()
    Object.entries(product).forEach(([key, value]) => payload.append(key, value))
    payload.append('image', image)

    const { data } = await api.post('/products/', payload, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  },
}

/** Actualiza un producto del catalogo (HU10). */
productsService.update = async function update(id, product, image) {
  if (!image) {
    const { data } = await api.patch(`/products/${id}/`, product)
    return data
  }

  const payload = new FormData()
  Object.entries(product).forEach(([key, value]) => payload.append(key, value))
  payload.append('image', image)

  const { data } = await api.patch(`/products/${id}/`, payload, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

/** Cambia el estado activo de un producto (HU10). */
productsService.setActive = async function setActive(id, isActive) {
  const { data } = await api.patch(`/products/${id}/`, { is_active: isActive })
  return data
}

/** Formatea un valor en pesos colombianos, sin decimales. */
export function formatPrice(value) {
  if (value === undefined || value === null) return ''
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'COP',
    maximumFractionDigits: 0,
  }).format(value)
}
