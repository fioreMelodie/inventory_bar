# HU22 - Consulta de pedidos pendientes de caja

Entrega local del 25 de octubre de 2026.

## Alcance implementado

- Nueva pantalla Pending orders, ruta /cashier/pending, accesible desde el
  menu y los accesos rapidos de Administrator y Cashier.
- API GET /api/orders/pending/ exclusiva de esos roles.
- Solo incluye pedidos IN_CASHIER; el cajero recibe los de su sede incluso
  si solicita otra mediante parametros. El administrador puede consultar
  todas las sedes o filtrar por una.
- Orden ascendente por hora de envio a caja, con identificador como desempate.
  No se ordena por apertura. Los registros antiguos sin hora de envio quedan
  al final y muestran Not recorded, sin inventar una hora.
- Cada pedido muestra numero, mesa, sede, mesero, hora de envio, tiempo de
  espera y total. Permite consultar los items y regresar a la bandeja.
- Actualizacion automatica mediante consulta cada cinco segundos despues de
  finalizar la anterior; no se superponen consultas ni se recarga la pagina.
- Las consultas automaticas llevan X-Session-Activity: background y no
  mantienen abierta una sesion que ya esta inactiva.
- Se recorren todas las paginas de la API; no existe el limite de ocho
  pedidos que tiene el resumen del inicio.
- Una respuesta antigua no reemplaza el resultado de un filtro mas reciente.
- Estados de carga, vacio y error; reintento manual y marca de ultima consulta.
  Tras fallar una actualizacion se conserva la ultima informacion recibida,
  con aviso visible de error.
- La pantalla de inicio del cajero tambien ordena sus pendientes por envio.

## Dependencias abiertas

HU22 queda implementada en su alcance de consulta. El inicio del cobro desde
el detalle depende de HU23/HU24 y aun no se incorpora ni se simula con un
boton sin funcionalidad.

La API excluye cualquier pedido que deje de estar IN_CASHIER y la interfaz
retira pedidos ausentes en la siguiente consulta. La desaparicion despues de
un pago efectivo se verificara cuando exista el flujo de pago y estado PAID.
No se certifica ese escenario con un pago real en esta entrega.

No se cambian las reglas de stock ni los estados almacenados de las mesas.
No se agregan modelos ni migraciones; los datos operativos se conservan.

## Verificacion

- Doce pruebas nuevas del backend: autenticacion, roles, sedes, orden FIFO,
  desempate, datos del detalle, filtros invalidos, paginacion, llegada de un
  pedido y salida de la cola al dejar de estar pendiente.
- Suite completa del backend: 302 pruebas aprobadas.
- Suite de navegador: 35 pruebas aprobadas y un duplicado de anchos omitido.
  Incluye comprobaciones de HU22 en escritorio y movil, error y recuperacion,
  acceso al detalle y regreso, llegada y retirada de pedidos y lectura de
  todas las paginas.
- Las pruebas de actualizacion usan respuestas interceptadas en el navegador.
  No crean pedidos en MySQL de presentacion.
- Las pruebas de escritura del backend usan la base temporal de Django.
- Compilacion Vite correcta y sin migraciones pendientes de generar.

Siguiente historia: HU23, pago en efectivo, considerando la dependencia de
generacion de factura descrita en HU25.

## Integracion posterior con HU23

El 25 de octubre de 2026 se incorpora Pay in cash al detalle para Cashier y
Administrator cuando el pedido esta IN_CASHIER. Un pago confirmado lo pasa
a PAID y lo excluye de la bandeja. El escenario se verifica en la base de
pruebas, no cobrando los pedidos de presentacion.
