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

| ID | Historia de Usuario | Módulo | Prioridad | SP | Rama |
| -- | ------------------- | ------ | --------- | -- | ---- |
| HU27 | Reporte de ventas, Administrador (todas las sedes) | Reportes | Alta | 5 | `feature/HU-27-reporte-ventas-admin` |
| HU28 | Reporte de ventas, Cajero (sede propia) | Reportes | Alta | 3 | `feature/HU-28-reporte-ventas-cajero` |
| HU29 | Filtrar reporte por criterios combinados | Reportes | Media | 5 | `feature/HU-29-filtros-combinados` |
| HU30 | Consultar log de eventos del sistema | Auditoría | Media | 5 | `feature/HU-30-log-de-eventos` |

## Entregables semanales

- **Semana 1 (19 — 25 oct):** HU27 · HU28 — 8 SP
- **Semana 2 (26 oct — 01 nov):** HU29 · HU30 — 10 SP

## Sprint Review

| Campo | Valor |
| ----- | ----- |
| Story Points comprometidos | 18 SP |
| Story Points completados | 18 SP |
| Historias aceptadas | 4 de 4 |

### Incremento entregado

- Reporte de ventas agrupado por día, sede y producto, construido únicamente sobre pedidos
  pagados, con cantidad vendida, valor de compra, valor de venta y ganancia.
- El Cajero obtiene el mismo reporte limitado a su sede y sin margen.
- Filtros de fecha, sede, producto y categoría combinables entre sí.
- Log de eventos del sistema con filtros por fecha, usuario, tipo de evento y sede, y detalle
  completo de cada registro.

## Decisiones técnicas del sprint

1. **El valor de compra se congela en el ítem del pedido.** La ganancia debe calcularse con el
   costo vigente al momento de la venta. Si se tomara el costo actual del catálogo, cambiar un
   precio de compra reescribiría la rentabilidad histórica. La migración completó los ítems ya
   existentes con el costo actual de su producto, que es la mejor aproximación disponible porque
   ese dato no se guardaba antes.
2. **El margen se retira en el servidor, no se oculta en la interfaz.** El reporte del Cajero no
   incluye valor de compra ni ganancia en la respuesta de la API. Ocultarlo solo en pantalla
   dejaría el dato accesible para cualquiera que mirase la petición.
3. **La sede del reporte se resuelve en el servidor.** El Cajero queda fijado a su sede aunque
   envíe el parámetro de otra.
4. **Índice sobre estado y fecha de pago del pedido.** Sin él, el reporte recorrería toda la
   tabla de pedidos. El reporte se resuelve con una única consulta de agregación, de modo que el
   número de filtros aplicados no afecta el tiempo de respuesta.
5. **Un filtro inválido devuelve error, no se ignora.** Pedir una sede o un producto inexistente
   responde 404 en lugar de entregar un reporte más amplio que el solicitado, que el usuario
   podría interpretar como válido.
6. **La sede se incorpora al log de auditoría.** La HU30 exige filtrar por sede, pero el modelo
   de eventos no la guardaba. Se añadió el campo y se propagó desde los módulos que la conocen;
   las acciones de parametrización global quedan sin sede porque no pertenecen a ninguna.

## Defectos detectados y corregidos

Durante la HU27, dos errores en la consulta de agregación, ambos detectados por las pruebas antes
de integrar:

1. Un alias llamado `product_id` colisionaba con el campo del propio modelo.
2. Un alias llamado `quantity` tapaba el campo `quantity`, de modo que las sumas de importes
   intentaban operar sobre un agregado en lugar de sobre el campo.

## Retrospectiva — Start / Stop / Continue

**Start**
- Verificar los requisitos no funcionales con pruebas, no por inspección. El tiempo de respuesta
  del reporte y del log se mide sobre volúmenes realistas.

**Stop**
- Asumir que una restricción de visibilidad se resuelve en la interfaz. La información que un rol
  no debe ver no debe salir del servidor.

**Continue**
- Una prueba por criterio de aceptación. Es lo que permitió cerrar las 30 historias con la
  Definition of Done cumplida y verificable, y lo que detectó los defectos de este sprint y del
  Sprint 3 antes de integrarlos.

## Cierre del proyecto

Con este sprint se completa el backlog: **30 historias de usuario, 122 Story Points, 5 sprints**.
Todas las historias fueron aceptadas y ningún Story Point quedó pendiente.
