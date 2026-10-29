# Sprint 4 — Pagos y Facturación

| Campo | Valor |
| ----- | ----- |
| Fechas | 05 — 18 de octubre de 2026 |
| Duración | 2 semanas |
| Story Points | 24 SP |
| Historias | HU22 · HU23 · HU24 · HU25 · HU26 |

## Sprint Goal

Cerrar el ciclo comercial: que el cajero vea los pedidos que llegan a caja, registre el cobro en
efectivo o con tarjeta, y que cada pago genere la factura que soporta la transacción y queda
disponible para consulta.

## Sprint Backlog

| ID | Historia de Usuario | Módulo | Prioridad | SP | Rama |
| -- | ------------------- | ------ | --------- | -- | ---- |
| HU22 | Consultar pedidos activos (Cajero) | Pedidos | Alta | 3 | `feature/HU-22-panel-pedidos-caja` |
| HU23 | Procesar pago en efectivo | Pagos y Facturación | Alta | 5 | `feature/HU-23-pago-efectivo` |
| HU24 | Procesar pago con tarjeta | Pagos y Facturación | Alta | 8 | `feature/HU-24-pago-tarjeta` |
| HU25 | Generar factura | Pagos y Facturación | Alta | 5 | `feature/HU-25-generar-factura` |
| HU26 | Consultar historial de facturas | Pagos y Facturación | Media | 3 | `feature/HU-26-historial-facturas` |

## Entregables semanales

- **Semana 1 (05 — 11 oct):** HU22 · HU23 — 8 SP
- **Semana 2 (12 — 18 oct):** HU24 · HU25 · HU26 — 16 SP

## Sprint Review

| Campo | Valor |
| ----- | ----- |
| Story Points comprometidos | 24 SP |
| Story Points completados | 24 SP |
| Historias aceptadas | 5 de 5 |

### Incremento entregado

- Panel de pedidos pendientes de cobro, en orden de llegada, que se refresca solo.
- Cobro en efectivo con validación del monto recibido y cálculo del cambio.
- Cobro con tarjeta de crédito o débito, con confirmación manual de la aprobación en datáfono.
- Factura automática por cada pago, con numeración consecutiva por sede, imprimible y de
  consulta inmediata.
- Historial de facturas con filtros de fecha, número y sede.

## Decisiones técnicas del sprint

1. **El cobro ocurre en una sola transacción.** Generar la factura, pasar el pedido a PAGADO y
   liberar la mesa son inseparables: si fallaran por separado, podría quedar un pedido cobrado
   sin factura o una mesa ocupada sin pedido activo.
2. **El consecutivo de factura se asigna bloqueando la sede.** Dos cajeros cobrando al mismo
   tiempo en la misma sede obtendrían el mismo número si se leyera el último y se sumara uno sin
   bloqueo.
3. **Facturas inmutables por partida doble.** El conjunto de vistas no expone escritura y el
   modelo bloquea `save()` sobre registros existentes y `delete()`. Cumple el requisito de que
   una venta registrada no pueda modificarse ni anularse bajo ningún perfil.
4. **Sin integración con pasarela de pago.** El datáfono es externo, tal como establece la
   propuesta. La factura no almacena código de autorización, número de tarjeta ni identificador
   de transacción externa; hay una prueba que lo verifica para evitar que se incorporen después
   sin decisión explícita.
5. **Un único método de pago por pedido.** La factura guarda un solo método y un pedido admite
   una sola factura, de modo que efectivo y tarjeta no pueden combinarse.

## Retrospectiva — Start / Stop / Continue

**Start**
- Escribir pruebas que verifiquen lo que el sistema **no** debe tener, no solo lo que debe
  hacer. La prueba de que la factura no guarda datos de pasarela documenta una decisión de
  alcance que de otro modo se perdería.

**Stop**
- Dar por cubierto un criterio porque "el modelo lo impide". La inmutabilidad de la factura se
  verifica tanto por la API como por el modelo, porque son dos caminos distintos de acceso.

**Continue**
- Transacciones atómicas en toda operación que toque más de una entidad.

## Preparación del Sprint 5

El Sprint 5 (19 oct — 01 nov) aborda reportes y auditoría: HU27 a HU30, 18 SP. Los pedidos
pagados, con sus ítems a precio congelado y su fecha de pago, son la base del reporte de ventas;
el log de auditoría existe desde el Sprint 1 y solo falta exponerlo con filtros.
