import api, { listAll } from './api'

/** Módulo 5 - Gestión de Proveedores. */
export const suppliersService = {
  /** Lista el directorio de proveedores. */
  async list() {
    return listAll('/suppliers/')
  },

  /** Registra un proveedor (HU12). */
  async create(supplier) {
    const { data } = await api.post('/suppliers/', supplier)
    return data
  },

  /** Actualiza los datos de contacto de un proveedor (HU12). */
  async update(id, supplier) {
    const { data } = await api.patch(`/suppliers/${id}/`, supplier)
    return data
  },

  /** Elimina un proveedor del directorio (HU12). */
  async remove(id) {
    await api.delete(`/suppliers/${id}/`)
  },

  /** Productos que suministra un proveedor (HU13). */
  async listProducts(id) {
    const { data } = await api.get(`/suppliers/${id}/products/`)
    return data
  },

  /**
   * Define la lista completa de productos del proveedor (HU13).
   * Los productos omitidos quedan desvinculados.
   */
  async setProducts(id, productIds) {
    const { data } = await api.put(`/suppliers/${id}/products/`, { products: productIds })
    return data
  },
}
