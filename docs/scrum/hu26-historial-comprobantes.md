# HU26 - Historial de comprobantes

Fecha: 2026-10-25.

## Alcance

Se completa la historia individual HU26 CONSULTAR HISTORIAL DE FACTURAS
sobre el panel Receipts de HU25, sin duplicar comprobantes ni crear otro
flujo de pago. Se conserva la denominacion de comprobante interno; no se
incorpora facturacion electronica o fiscal.

## Criterios y comportamiento

- Administrator consulta todas las sedes, incluidas las inactivas.
- Cashier solo consulta la sede asignada. Waiter no accede al historial.
- Filtros From date, Through date y Receipt number. Numero admite coincidencia
  parcial, sin distinguir mayusculas; los caracteres de comodin son literales.
- Los filtros de fecha, numero y sede se combinan con AND en servidor, siempre
  despues de restringir el alcance del rol. Ningun filtro amplia los permisos.
- Fechas en America/Bogota: inicio a las 00:00 inclusive y final hasta la
  medianoche siguiente exclusiva. Se admiten ambos extremos o solo uno.
- Sin filtros se consulta todo el historial, sin limite implicito de antiguedad.
- El servidor rechaza fechas invalidas o rangos invertidos con 400. El formulario
  tambien detecta un rango invertido antes de enviar la consulta.
- Apply filters y cambiar sede reinician la paginacion. Cambiar pagina conserva
  todos los filtros. La URL permite recargar o volver del detalle sin perderlos.
- Clear filters elimina fechas, numero y sede y vuelve a la primera pagina.
- No matching receipts diferencia una busqueda vacia de No receipts yet.
- Listado con numero, fecha/hora de Bogota, mesa, sede, total y metodo; detalle
  completo e impresion permanecen disponibles. No hay edicion o eliminacion.

## API

GET /api/invoices/?start_date=2026-10-01&end_date=2026-10-25&number=V001&venue=1&page=1

Fechas ISO YYYY-MM-DD; numero hasta 60 caracteres; sede numerica positiva.
Se mantienen respuesta paginada, 25 registros por pagina y orden descendente
por fecha e ID. El detalle mantiene los permisos existentes.

Los limites de fecha se calculan en Python y se consultan como instantes;
no se depende de tablas de zonas horarias instaladas en MySQL.
El extremo maximo representable 9999-12-31 no se incrementa, evitando overflow.
No hay migraciones, cambios de datos historicos ni politicas de eliminacion.

## Verificacion

Pruebas de limites del dia, ano bisiesto, fecha invalida, rango invertido,
extremos individuales, antiguedad, coincidencia parcial/literal y filtros
combinados por rol. Las pruebas de interfaz comprueban formulario, URL,
recarga, paginacion, detalle, limpieza y adaptacion a escritorio y movil.
Se usan respuestas interceptadas; no se registran pagos reales.

Huella operativa coincidente antes y despues de la validacion:
adfd9e09bf626abe01126b5a47f138718275c55f3fcc3976bf27bdc9497d1055.

Resultados de cierre:

- 369 pruebas de backend aprobadas en MySQL aislado, incluidas las cinco
  de concurrencia. Contenedor y base temporal eliminados al terminar.
- Suite completa de interfaz: 67 aprobadas y una comprobacion duplicada de
  dimensiones omitida intencionalmente.
- Las seis pruebas especificas de HU26 tambien aprobaron tras agregar la
  comprobacion visual adicional a 320 y 768 pixeles.
- Capturas revisadas a 320, 390, 768 y 1440 pixeles, sin desbordamientos.
- Compilacion Vite correcta, sin migraciones pendientes y git diff --check limpio.
- Se conserva el pago y comprobante existentes, sin crear pagos reales en las
  pruebas. Los cambios estan desplegados solo en la aplicacion local; sin push.
