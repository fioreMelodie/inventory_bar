# HU27 - Reporte de ventas del administrador

Fecha: 2026-10-25.

## Alcance

Nuevo Reports > Sales report, exclusivo para Administrator, con consulta
consolidada o por sede, incluidas sedes inactivas. HU28 documenta por separado
el reporte del cajero, sin acceso a ventas de otras sedes para ese perfil.

Se usan exclusivamente comprobantes asociados a pedidos PAID. Fechas por
dia completo en America/Bogota, sin limite implicito de antiguedad. HU29
actualiza este flujo: ambos extremos de fecha son obligatorios al generar.
Filtros combinables: fechas, sede, ID o nombre parcial del producto y categoria.
El codigo del producto es su ID existente, sin inventar un nuevo SKU.

Cada linea conserva fecha, comprobante, sede, producto, categoria y cantidad;
valor de compra = cantidad por precio de compra guardado al registrar el pago;
valor de venta = subtotal historico; ganancia = venta menos compra.
Los totales abarcan todos los resultados filtrados, no solo la pagina visible.
No se hace calculo de costo medio de inventario, impuestos o utilidad neta.

## Integridad historica

Los comprobantes anteriores no guardaban precio de compra ni categoria.
No se reescriben ni se utiliza el catalogo actual para inventar esos valores.
Se incluyen sus ventas, pero los valores desconocidos se muestran Not recorded.
Si alguna linea filtrada no tiene costo, los totales de compra y ganancia quedan
no disponibles, con advertencia y conteo de las lineas afectadas.
Las ganancias historicas completas quedan condicionadas a disponer de una
fuente verificable de costos; no se declara resuelto ese dato faltante.

Los pagos nuevos guardan purchase_price y category dentro del snapshot
inmutable del comprobante. El precio de compra es el valor del catalogo en
el momento de registrar el pago, no un costo reconstruido del inventario.
Los cambios posteriores del catalogo no modifican la ganancia ya registrada.
El costo se excluye de las respuestas del comprobante de cliente; solo el
reporte autorizado lo utiliza. No se crea ninguna migracion.

## Consulta y salidas

- GET /api/reports/sales/: paginacion de 25 lineas y resumen del conjunto.
- Parametros: start_date, end_date, venue, product, category y page.
- category=__unrecorded__ permite consultar las categorias historicas ausentes.
- export=csv entrega todas las lineas filtradas, independientemente de page.
- export=print entrega todas las lineas para imprimir el reporte completo.
- Fechas exportadas con desplazamiento -05:00 de Bogota para fechas actuales.
- CSV protege los nombres que podrian interpretarse como formulas al abrirlos
  en una hoja de calculo. Los importes se exportan como enteros COP.
- Salidas sin cache y con permisos en servidor. Cashier y Waiter reciben 403;
  no autenticado recibe 401. La consulta no crea pagos ni modifica registros.
- La impresion incluye filtros y totales; no imprime solo la pagina actual.

## Verificacion

Pruebas de estados, filtros combinados, fechas, sedes inactivas, antiguedad,
totales entre paginas, exportacion completa, permisos, costo desconocido,
inmutabilidad de datos y proteccion de costos en el comprobante.
Las pruebas de navegador interceptan ventas y exportaciones de ejemplo;
no generan pagos en la base de presentacion. MySQL temporal separado para
la regresion del servidor.

Huella operativa coincidente antes y despues de la validacion:
7e61875f341190145cac17451d29cf5f77cc0f21d9a11e32d92edd1111448ddf.

Resultados de cierre:

- 382 pruebas de backend aprobadas en MySQL aislado, incluidas las cinco
  de concurrencia. Contenedor y base temporal eliminados al terminar.
- Suite completa de interfaz: 77 aprobadas y una comprobacion duplicada de
  dimensiones omitida intencionalmente.
- Tras ajustar importes a 320 pixeles y el ciclo afterprint, las diez pruebas
  especificas de HU27 aprobaron nuevamente.
- Capturas revisadas a 320, 390, 768 y 1440 pixeles, y reporte completo en
  modo impresion. No hay importes partidos a 320 pixeles.
- Compilacion Vite correcta, sin migraciones nuevas y git diff --check limpio.
- Lectura de los datos actuales: tres transacciones, cinco lineas, trece
  unidades, ventas por 168500 COP. Las cinco lineas anteriores no tienen
  costo historico guardado y no se les asigno una ganancia inventada.
- No se crearon pagos en la base de presentacion durante las pruebas.
- Despliegue local en http://127.0.0.1:8088/reports/sales; sin commit ni push.

La HU27 queda disponible con la limitacion explicita de costos/categorias
anteriores ausentes; la reconstruccion de esos valores requiere una fuente
verificable y una decision posterior, sin alterar comprobantes inmutables.
