# Validacion por roles

Fecha: 24 de octubre de 2026.
Base de trabajo: inventory_bar_actualizado, rama trabajo-local.

## Alcance de esta etapa

Validar la version local despues del cambio de idioma y del rediseno.
No se implementan pagos ni se publica al repositorio remoto.

| Rol o flujo | Comprobacion |
| --- | --- |
| Administrator | Navegacion de administracion, catalogo, formularios y filtros. Creacion de producto y mesa mediante API en base temporal. |
| Waiter | Catalogo sin precio de compra; sin gestion de usuarios ni inventario; mesas y pedidos limitados a su sede. |
| Cashier | Catalogo sin precio de compra; inventario limitado a su sede; pedidos de solo lectura. |
| Preparacion | El cajero registra existencias en su sede, en base temporal. |
| Pedido abierto | El waiter abre una mesa libre, agrega tres unidades de cafe y el stock baja de 20 a 17; total de 9000. |
| Propiedad del pedido | Otro waiter no puede agregar productos al pedido; el cajero no puede enviarlo a caja. |
| Envio a caja | El pedido cambia a IN_CASHIER y aparece entre los pendientes del cajero de la misma sede. |
| Inmutabilidad | Tras el envio no se admiten mas productos ni cancelacion; el stock no vuelve a descontarse. |
| Estado de mesa | Permanece OCCUPIED con active_order_status IN_CASHIER. |
| Cancelacion previa | Cancela un pedido OPEN, repone el stock a 20 y libera la mesa. No aparece entre pendientes de caja. |
| Otra sede | Un cajero de otra sede no puede consultar el pedido por su identificador. |
| Auditoria | El envio registra ORDER_SENT_TO_CASHIER asociado al pedido. |

## Evidencia automatizada

- frontend/tests/interface.spec.js: comprobaciones de escritorio y movil.
  Se agregan pruebas de privacidad del catalogo, API de usuarios, inventario,
  alcance por sede y ausencia de controles de edicion en pedidos de solo lectura.
- backend/apps/orders/tests/test_role_workflow.py: dos recorridos integrados
  con inicio de sesion JWT real y peticiones a la API.
- Las operaciones de escritura del recorrido integrado se ejecutan en una
  base SQLite temporal creada y destruida por Django, no en MySQL de presentacion.
- En la aplicacion Docker/MySQL se hacen consultas y pruebas de interfaz.
  No se crean ni modifican productos, mesas, usuarios, stock o pedidos.
  Los accesos y cierres de sesion generan la auditoria habitual.
- Resultado de navegador: 25 pruebas aprobadas. Se omite un caso duplicado
  de anchos en movil, que ya se ejecuta en el proyecto de escritorio.
- Resultado de la suite completa del backend: 290 pruebas aprobadas,
  incluidos los dos recorridos integrados nuevos.

Estas pruebas no sustituyen una aceptacion manual del docente ni pruebas de
concurrencia sobre MySQL.

## Siguiente etapa

1. Revisar las alertas de dependencias documentadas en
   mejoras-experiencia-usuario.md y verificar compatibilidad de las correcciones.
2. Contrastar con el backlog el alcance de cobros y los siguientes entregables
   antes de implementar historias posteriores.
3. Preparar el guion de demostracion por rol para la presentacion.

El desarrollo validado llega al envio del pedido a caja. Cobro, confirmacion
del pago y liberacion de la mesa por pago no quedan certificados ni implementados
por esta etapa.
