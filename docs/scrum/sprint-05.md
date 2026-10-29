# Sprint 5 — Reportes y Auditoría

| Campo | Valor |
| ----- | ----- |
| Fechas | 19 de octubre — 01 de noviembre de 2026 |
| Duración | 2 semanas |
| Story Points | 18 SP |
| Historias | HU27 · HU28 · HU29 · HU30 |

## Sprint Goal

Cerrar el proyecto dando visibilidad gerencial: reportes de ventas con márgenes para el
Administrador, reportes acotados para el Cajero, filtros combinables y el log de auditoría
consultable que garantiza la trazabilidad de todo lo ocurrido en el sistema.

## Sprint Backlog

| ID | Historia de Usuario | Módulo | Prioridad | SP |
| -- | ------------------- | ------ | --------- | -- |
| HU27 | Reporte de ventas, Administrador (todas las sedes) | Reportes | Alta | 5 |
| HU28 | Reporte de ventas, Cajero (sede propia) | Reportes | Alta | 3 |
| HU29 | Filtrar reporte por criterios combinados | Reportes | Media | 5 |
| HU30 | Consultar log de eventos del sistema | Auditoría | Media | 5 |

El detalle de cada historia está documentado por separado en
`hu27-reporte-ventas-administrador.md` a `hu30-log-eventos.md`.

## Sprint Review

| Campo | Valor |
| ----- | ----- |
| Story Points comprometidos | 18 SP |
| Story Points completados | 18 SP |
| Historias aceptadas | 4 de 4 |

### Incremento entregado

- Reporte de ventas construido sobre comprobantes de pedidos pagados, con fecha, sede, producto,
  categoría, cantidad, valor de compra, valor de venta y ganancia.
- El Cajero obtiene el mismo reporte limitado a su sede y sin acceso al margen.
- Filtros de fecha, sede, producto y categoría combinables con AND.
- Log de eventos con filtros por fecha, usuario, tipo y sede, con detalle por evento.

## Decisiones técnicas del sprint

1. **El valor de compra se toma del registrado al cobrar, no del catálogo actual.** Cambiar hoy
   un precio de compra no debe reescribir la rentabilidad histórica.
2. **Los comprobantes anteriores al cambio no se reescriben.** Los que no guardaban precio de
   compra ni categoría se muestran como *Not recorded* en lugar de inventar el dato con el
   catálogo actual. Sus ventas sí se incluyen; solo los totales de compra y ganancia quedan
   marcados como incompletos. Es preferible un reporte que admite lo que no sabe a uno que
   presenta una cifra inventada como si fuera un hecho.
3. **El margen se retira en el servidor para el Cajero**, no se oculta en la interfaz. Ocultarlo
   solo en pantalla dejaría el dato accesible en la petición.
4. **Los totales abarcan todos los resultados filtrados**, no solo la página visible.
5. **Fechas por día completo en America/Bogota**, con validación del orden del rango.
6. **En el log de auditoría las fechas son opcionales**; en el reporte de ventas, obligatorias.
   La HU29 impone el rango sobre los reportes, no sobre la consulta de auditoría.
7. **El detalle del evento conserva la marca de tiempo original completa**, sin truncar la
   precisión, junto a la hora legible en Bogota.
8. **El código de producto es su identificador existente**, sin introducir un SKU nuevo que no
   pide ninguna historia.

## Ajustes solicitados en la revisión del docente

Incorporados el 23 de octubre y documentados en `ajustes-revision-docente.md`:

- **El precio de venta no puede ser inferior al de compra.** Validado en el formulario y en la
  API, tanto al crear como al editar. Una solicitud rechazada no guarda el producto ni registra
  una modificación exitosa en la auditoría. No se alteran precios existentes ni los congelados
  en pedidos históricos.
- **Tipo y categoría pasan a listas desplegables**, sin texto libre desde la interfaz.
- **Preparación de datos para la presentación**, con respaldo previo de MySQL y conservando el
  historial de auditoría.

## Retrospectiva — Start / Stop / Continue

**Start**
- Distinguir en los reportes el dato ausente del dato cero. *Not recorded* comunica algo
  distinto de un cero, y confundirlos induce a error en una decisión de negocio.

**Stop**
- Rellenar huecos del histórico con valores actuales. Un reporte inventado es peor que un
  reporte incompleto.

**Continue**
- Una prueba por criterio de aceptación, y pruebas de interfaz sobre los flujos completos.

## Cierre del proyecto

Con este sprint se completa el backlog: **30 historias de usuario, 122 Story Points, 5 sprints**.
Todas las historias fueron aceptadas y ningún Story Point quedó pendiente.
