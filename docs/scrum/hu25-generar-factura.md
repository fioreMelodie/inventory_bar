# HU25 - Generacion y consulta de comprobantes

Fecha: 2026-10-25.

## Alcance

Se completa la historia individual HU25 GENERAR FACTURA. En la interfaz se
mantiene Payment receipt: es un comprobante interno de la transaccion, no
una declaracion de cumplimiento fiscal ni una factura electronica.

No se agregan impuestos, emision fiscal, correo, anulaciones o reembolsos.
La consulta historica avanzada se completa en HU26, documentada por separado.

## Criterios cubiertos

- La generacion sigue siendo automatica al registrar efectivo, credito o
  debito; no requiere otra accion. Pago, comprobante, auditoria y cierre del
  pedido pertenecen a la misma transaccion.
- Numero unico, secuencial por sede, protegido por restricciones y bloqueos.
- El detalle conserva fecha/hora, sede, mesa, mesero, cajero, productos,
  cantidades, precios unitarios, total y metodo. Usa la copia inmutable,
  no nombres o precios actuales del catalogo.
- Nuevo panel Receipts, accesible desde Operations para Administrator y
  Cashier. Incluye paginacion de 25 registros, mas recientes primero,
  actualizacion manual y filtro de sede para Administrator, incluidas
  las sedes inactivas. El regreso desde el detalle conserva filtro y pagina.
- Cashier solo consulta su sede; Administrator puede consultar todas.
  Waiter no accede al panel ni a los endpoints. Los filtros nunca amplian
  el alcance autorizado en servidor.
- Visualizacion e impresion desde Print receipt. La impresion oculta
  navegacion y controles y conserva el comprobante.
- No hay acciones de edicion o anulacion; los endpoints de consulta
  rechazan escritura. Se conservan las protecciones de modelos y admin.

## API

- GET /api/invoices/?page=1&venue=1: listado paginado y acotado por rol.
- GET /api/invoices/<id>/: comprobante completo, con el mismo alcance.
- El listado usa datos historicos de snapshot sin devolver todos los items.
- Filtro de sede invalido: 400; pagina fuera de rango: 404.
- Sede sin comprobantes o filtro fuera del alcance del cajero: lista vacia.
- No se agregan migraciones ni se reescriben comprobantes anteriores.

## Verificacion

Las pruebas de generacion, secuencia, concurrencia, reintentos, atomicidad e
inmutabilidad de HU23/HU24 siguen en la regresion. HU25 agrega pruebas de
listado, paginacion, filtros, permisos y conservacion de valores historicos.
Las pruebas de navegador usan respuestas interceptadas para paginacion,
errores e impresion, y lecturas reales para el panel del cajero. No crean
pagos o datos de presentacion.

Huella operativa coincidente antes y despues de validar HU25:
adfd9e09bf626abe01126b5a47f138718275c55f3fcc3976bf27bdc9497d1055.

Resultados de cierre:

- 361 pruebas de backend aprobadas en MySQL temporal, incluidas las cinco
  de concurrencia. Base y contenedor temporales eliminados al terminar.
- Suite completa de interfaz: 61 aprobadas y una comprobacion duplicada de
  dimensiones omitida intencionalmente. Tras el ajuste de sedes inactivas,
  las ocho pruebas especificas de HU25 tambien aprobaron.
- Compilacion Vite correcta, sin nuevas migraciones y git diff --check limpio.
- Capturas revisadas en escritorio y movil para el panel y el modo impresion.
- El despliegue es local en http://127.0.0.1:8088/invoices; no se hace push.
