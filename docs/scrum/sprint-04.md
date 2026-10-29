# Sprint 4 — Pagos y Facturación

| Campo | Valor |
| ----- | ----- |
| Fechas | 05 — 18 de octubre de 2026 |
| Duración | 2 semanas |
| Story Points | 24 SP |
| Historias | HU22 · HU23 · HU24 · HU25 · HU26 |

## Sprint Goal

Cerrar el ciclo comercial: que el cajero vea los pedidos que llegan a caja, registre el cobro en
efectivo o con tarjeta, y que cada pago genere el comprobante que soporta la transacción y queda
disponible para consulta.

## Sprint Backlog

| ID | Historia de Usuario | Módulo | Prioridad | SP |
| -- | ------------------- | ------ | --------- | -- |
| HU22 | Consultar pedidos activos (Cajero) | Pedidos | Alta | 3 |
| HU23 | Procesar pago en efectivo | Pagos y Facturación | Alta | 5 |
| HU24 | Procesar pago con tarjeta | Pagos y Facturación | Alta | 8 |
| HU25 | Generar factura | Pagos y Facturación | Alta | 5 |
| HU26 | Consultar historial de facturas | Pagos y Facturación | Media | 3 |

El detalle de cada historia, con su flujo e integridad, está documentado por separado en
`hu22-pedidos-pendientes.md` a `hu26-historial-comprobantes.md`.

## Sprint Review

| Campo | Valor |
| ----- | ----- |
| Story Points comprometidos | 24 SP |
| Story Points completados | 24 SP |
| Historias aceptadas | 5 de 5 |

### Incremento entregado

- Bandeja de pedidos pendientes de cobro, por sede y en orden de llegada.
- Cobro en efectivo con validación del importe recibido y cálculo del cambio en el servidor.
- Cobro con tarjeta de crédito o débito, con confirmación manual de la aprobación en datáfono y
  referencia de aprobación.
- Comprobante interno inmutable por cada pago, con consecutivo por sede.
- Historial de comprobantes con filtros, con alcance por rol.

## Decisiones técnicas del sprint

1. **Pago y comprobante son entidades separadas.** `Payment` registra la transacción y `Invoice`
   el documento que la soporta. Son cosas distintas y se modelan por separado.
2. **Idempotencia mediante referencia única.** Cada intento de cobro lleva una referencia UUID.
   Repetir la misma referencia sobre el mismo pedido e importe devuelve el pago y el comprobante
   ya creados, sin generar otro registro ni avanzar el consecutivo. Protege frente a la doble
   pulsación del cajero y frente al reintento automático de la red.
3. **El comprobante guarda una instantánea del pedido** (`snapshot`). El documento no depende de
   que los datos del pedido permanezcan intactos: se basta a sí mismo.
4. **Validación de `expected_total`.** El cliente envía el total que mostró en pantalla y el
   servidor lo contrasta con el calculado. Evita confirmar un cobro por un importe distinto del
   que vio el cajero.
5. **Consecutivo por sede con contador propio** (`InvoiceCounter`), bloqueado durante la
   transacción. Dos cajeros cobrando a la vez en la misma sede no pueden obtener el mismo número.
6. **Una sola transacción para todo el cobro.** Pago, comprobante, consecutivo, paso a PAID,
   liberación de la mesa y los eventos de auditoría se confirman juntos o no se confirma nada.
7. **Inmutabilidad por herencia** (`ImmutableRecord`). Pagos y comprobantes comparten el
   mecanismo que bloquea modificación y eliminación, también desde el panel de Django.
8. **Sin integración con pasarela de pago.** El datáfono es externo, conforme a la propuesta.

## Retrospectiva — Start / Stop / Continue

**Start**
- Documentar por escrito los acuerdos con el responsable del proyecto cuando el backlog general
  y las historias individuales difieren (`decisiones-requisitos.md`). Evita resolver la misma
  discrepancia dos veces con criterios distintos.

**Stop**
- Confiar en importes calculados por el cliente. El servidor recalcula el total y el cambio.

**Continue**
- Pruebas de concurrencia sobre las operaciones de dinero. Son las que verifican que la
  idempotencia y los bloqueos funcionan de verdad.

## Preparación del Sprint 5

El Sprint 5 (19 oct — 01 nov) aborda reportes y auditoría: HU27 a HU30, 18 SP. Los comprobantes
emitidos, con su instantánea y el precio de compra registrado al cobrar, son la base del reporte
de ventas; el log de auditoría existe desde el Sprint 1 y falta exponerlo con filtros.
