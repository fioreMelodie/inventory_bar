import api from './api'

/** Módulo 5 - Gestión de Proveedores. */
export const suppliersService = {
  /** Lista el directorio de proveedores. */
  async list() {
    const { data } = await api.get('/suppliers/')
    return data.results ?? data
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
}
