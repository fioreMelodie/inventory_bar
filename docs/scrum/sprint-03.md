# Sprint 3 — Mesas y Pedidos

| Campo | Valor |
| ----- | ----- |
| Fechas | 21 de septiembre — 04 de octubre de 2026 |
| Duración | 2 semanas |
| Story Points | 26 SP |
| Historias | HU17 · HU18 · HU19 · HU20 · HU16 · HU21 |

## Sprint Goal

Poner en funcionamiento la operación de sala: configurar las mesas de cada sede, visualizar su
estado en tiempo real, abrir pedidos asociados a una mesa, registrar los productos solicitados
descontando el inventario en ese mismo momento, y trasladar el pedido al cajero de forma
definitiva.

## Sprint Backlog

| ID | Historia de Usuario | Módulo | Prioridad | SP | Rama |
| -- | ------------------- | ------ | --------- | -- | ---- |
| HU17 | Crear y configurar mesas por sede | Gestión de Mesas | Alta | 3 | `feature/HU-17-crear-mesas` |
| HU19 | Crear pedido (Mesero) | Pedidos | Alta | 5 | `feature/HU-19-crear-pedido` |
| HU18 | Consultar vista de sala y estado de mesa | Gestión de Mesas | Alta | 5 | `feature/HU-18-vista-de-sala` |
| HU16 | Descuento automático de stock al crear un pedido | Inventario / Pedidos | Alta | 5 | `feature/HU-16-descuento-automatico-stock` |
| HU20 | Agregar productos a un pedido | Pedidos | Alta | 5 | `feature/HU-20-agregar-productos-pedido` |
| HU21 | Enviar pedido a caja | Pedidos | Alta | 3 | `feature/HU-21-enviar-pedido-caja` |

## Reordenamiento del sprint

El backlog proponía el orden HU17 · HU18 · HU19 · HU20 · HU16 · HU21. Durante el Sprint
Planning se detectaron dos dependencias que obligaban a alterarlo, sin cambiar el alcance ni los
Story Points comprometidos:

1. **La HU19 se adelanta a la HU18.** Un criterio de aceptación de la vista de sala es que una
   mesa ocupada muestre *el tiempo transcurrido desde que se abrió el pedido*. Eso exige que la
   entidad Pedido exista antes de construir la vista; de lo contrario la historia se habría
   entregado incompleta y habría que retocarla después.
2. **La HU16 se adelanta a la HU20.** La HU20 establece que al agregar un producto *el sistema
   verifica el stock y lo descuenta inmediatamente*. Ese comportamiento es precisamente lo que
   define la HU16, de modo que desarrollar la HU20 primero habría significado entregarla sin uno
   de sus criterios de aceptación, o duplicar la lógica para rehacerla después.

La *Guía de Scrum para el proyecto Café Colombia Bar* contempla explícitamente este ajuste: la
distribución del backlog es una propuesta inicial, no un calendario rígido, y el equipo la ajusta
según capacidad, prioridades y aprendizaje.

## Entregables semanales

- **Semana 1 (21 — 27 sep):** HU17 · HU19 · HU18 — 13 SP
- **Semana 2 (28 sep — 04 oct):** HU16 · HU20 · HU21 — 13 SP

## Sprint Review

| Campo | Valor |
| ----- | ----- |
| Story Points comprometidos | 26 SP |
| Story Points completados | 26 SP |
| Historias aceptadas | 6 de 6 |
| Pruebas automatizadas | 256 en total, todas en verde |

### Incremento entregado

- Configuración de mesas por sede, sin límite de cantidad, con identificador único dentro de la
  sede. Las mesas no se eliminan: se inactivan, conservando el histórico de pedidos.
- Vista de sala que distingue mesas libres y ocupadas, indica cuánto lleva abierta cada orden y
  se refresca sola cada 10 segundos.
- Apertura de pedidos sobre mesas libres, con la mesa pasando automáticamente a OCUPADA.
- Registro de productos en el pedido con descuento de inventario en el mismo acto, acumulación
  de cantidades y recálculo automático del total.
- Envío del pedido a caja, tras lo cual el pedido queda inmutable.

## Decisiones técnicas del sprint

1. **Un solo pedido activo por mesa, garantizado en la base de datos.** Se usa una restricción de
   unicidad condicional (`status = OPEN`) en lugar de una validación de aplicación: dos meseros
   pulsando "Abrir pedido" a la vez sobre la misma mesa no pueden crear dos órdenes.
2. **El descuento de stock bloquea la fila con `select_for_update`.** Sin ese bloqueo, dos
   meseros agregando el último producto disponible al mismo tiempo podrían dejar el inventario
   en negativo.
3. **El precio unitario se congela en el ítem del pedido.** Cumple el criterio de la HU10 de que
   los cambios de precio solo afecten pedidos futuros, sin necesidad de versionar el catálogo.
4. **La cancelación de un pedido no lo elimina.** La HU16 exige reintegrar el stock de un pedido
   cancelado, pero la propuesta comercial establece que los pedidos no se eliminan. Se resolvió
   con un estado CANCELADO: el stock vuelve al inventario, la mesa se libera y el registro
   permanece para auditoría.
5. **Vista de sala por sondeo.** El requisito de actualización "en tiempo real" se cubre con un
   refresco cada 10 segundos. Para 20 usuarios concurrentes y un cambio de estado cada varios
   minutos, es suficiente y evita introducir WebSockets, que añadirían infraestructura no
   contemplada en la propuesta.

## Defecto detectado y corregido

Al desarrollar la HU20, las pruebas revelaron que el total del pedido quedaba desactualizado: el
método que lo recalculaba sumaba los ítems desde la relación cacheada por `prefetch_related`, de
modo que leía el estado anterior al cambio. Se corrigió calculando la suma en la base de datos.
El defecto no llegó a `develop`: lo detectaron las pruebas de la propia historia.

## Retrospectiva — Start / Stop / Continue

**Start**
- Revisar las dependencias entre historias **dentro** del sprint durante el Planning. En este
  sprint dos historias estaban mal ordenadas en el backlog y se detectó al empezar a
  desarrollarlas, no al planificarlas.

**Stop**
- Confiar en que una instancia de modelo refleja el estado actual de sus relaciones. El defecto
  del total del pedido vino de ahí. Cuando un cálculo depende de datos que acaban de cambiar, se
  consulta la base de datos.

**Continue**
- Escribir primero la prueba del criterio de aceptación y después el código. Es lo que hizo
  visible el defecto del total antes de integrarlo.
- Usar restricciones de base de datos para las reglas que no pueden romperse, en vez de
  validaciones de aplicación.

## Preparación del Sprint 4

El Sprint 4 (05 — 18 oct) aborda pagos y facturación: HU22 a HU26, 24 SP. Queda disponible lo que
necesita: pedidos en estado EN_CAJA visibles para el Cajero, con su total calculado, sus ítems
congelados a precio de venta y la mesa aún ocupada a la espera del cobro.
