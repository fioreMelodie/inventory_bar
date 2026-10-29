# HU28 - Reporte de ventas del cajero, sede propia

Fecha: 2026-10-25.

## Alcance de la historia

Reports > Sales report para Cashier, en /reports/my-sales.
La sede se muestra bloqueada a la asignada al usuario. Los unicos filtros
editables son rango de fechas y producto (ID o nombre). El listado muestra
fecha, producto, cantidad y valor de venta. Resumen de ventas y unidades
del conjunto filtrado, no solo de la pagina visible.

No se agregan graficas, categorias, exportacion o impresion al reporte del
cajero, pues no forman parte de esta historia. El reporte del administrador
de HU27 conserva sus funciones y permisos.

Solo incluye pedidos PAID. HU29 actualiza este flujo: se requieren ambas
fechas, sin limite de antiguedad dentro del rango elegido. Las fechas usan
dias completos de America/Bogota.
Se conserva paginacion de 25 lineas, filtros en la URL, validacion de rangos,
recarga, limpieza de filtros y estados vacio/error.

## Seguridad en servidor

- GET /api/reports/sales/own/, exclusivo de Cashier.
- La sede se obtiene del usuario autenticado, nunca de parametros del cliente.
- Sin sede asignada: 403, sin consulta global de ventas.
- Se aceptan solamente start_date, end_date, product y page.
- venue, category, export, number u otros parametros adicionales: 400.
- El alcance por sede se aplica antes de procesar lineas, totales o paginacion.
- Las respuestas usan una lista explicita de campos: id, issued_at, product_id,
  product_name, quantity y sale_value. Resumen: sales, quantity, transactions,
  currency. No se devuelven costos, ganancias, categorias ni datos de otra sede.
- El cajero sigue recibiendo 403 en el reporte/exportaciones del administrador.
- Waiter no tiene acceso a reportes. Administrator usa su endpoint de HU27.
- Consultas de solo lectura y Cache-Control: no-store.

## Verificacion

Pruebas de filtros combinados, fechas y limites del dia, antiguedad, pedidos
pagados, valores historicos, alcance entre paginas, usuario sin sede,
parametros manipulados, permisos y ausencia de campos privados.
Pruebas de navegador para menu, sede bloqueada, cuatro columnas, filtros,
recarga, paginacion, limpieza, errores, permisos y diseno adaptable.
No se generan pagos reales en la base de presentacion.

Huella operativa coincidente antes y despues de validar HU28:
7e61875f341190145cac17451d29cf5f77cc0f21d9a11e32d92edd1111448ddf.

Resultados de cierre:

- 393 pruebas de backend aprobadas en MySQL aislado, incluidas las cinco
  de concurrencia. Contenedor y base temporal eliminados al terminar.
- Suite completa de interfaz: 85 aprobadas y una comprobacion duplicada de
  dimensiones omitida intencionalmente.
- Capturas revisadas a 320, 390, 768 y 1440 pixeles, sin desbordamientos.
- Compilacion Vite correcta, sin migraciones nuevas y git diff --check limpio.
- Lectura real del endpoint del cajero: 200, cinco lineas de su sede; campos
  de linea y resumen verificados contra la lista publica permitida.
- Datos de presentacion preservados, sin pagos nuevos creados por las pruebas.
- Despliegue local en http://127.0.0.1:8088/reports/my-sales; sin commit ni push.
