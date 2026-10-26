# HU23 - Pago en efectivo

Entrega local del 25 de octubre de 2026.

## Flujo

1. Cashier o Administrator abre Pending orders y consulta un pedido.
2. Pay in cash muestra el total y solicita Amount received (COP).
3. El cambio se calcula como importe recibido menos total.
4. Confirm cash payment registra el pago y abre el comprobante interno.
5. El pedido pasa a PAID y deja la bandeja; su mesa pasa a FREE.

Waiter no puede cobrar ni acceder a comprobantes. Cashier solo opera su sede,
Administrator puede operar todas. No se cambian contrasenas ni asignaciones.

## Integridad

- El total se valida contra los items y los precios congelados del pedido.
- Solo se cobran pedidos IN_CASHIER con mesa ocupada y datos consistentes.
- Se requieren importes enteros positivos en COP, suficientes para cubrir el
  total. El servidor calcula el cambio; ignora importes derivados del cliente.
- expected_total evita confirmar un total distinto del mostrado en pantalla.
- Una transaccion guarda pago, comprobante, consecutivo por sede, estado
  PAID, liberacion de mesa y los dos eventos de auditoria.
- Si falla el comprobante o la auditoria, se revierte toda la operacion.
- No se modifica stock al cobrar: ya fue descontado al agregar los productos.
- Bloqueos de mesa, pedido y sede serializan confirmaciones concurrentes.
- Un unico pago por pedido y una referencia UUID unica evitan duplicados.
- Repetir la misma referencia, cajero, pedido e importe devuelve el mismo
  pago y comprobante, sin generar otro registro ni avanzar el consecutivo.
- Otra referencia sobre un pedido ya pagado devuelve conflicto.
- Reintentar despues de reabrir la mesa no vuelve a liberarla.
- La referencia de intento se conserva en sessionStorage para recuperar
  respuestas perdidas, sin guardar contrasenas ni tokens adicionales.
- Los pedidos PAID no admiten mas productos, cancelacion o envio a caja.
  Su edicion tambien queda bloqueada en el panel de Django.

## Comprobante interno

Se implementa la base de HU25 requerida por HU23: numero consecutivo por sede,
fecha, sede, mesa, mesero, cajero, items, cantidades, precios, total, efectivo
recibido y cambio. Los nombres y precios se copian al generar el documento,
para conservar el detalle aunque cambie el catalogo.

Pago y comprobante son inmutables desde el ORM del aplicativo y el panel
de Django; la API de comprobantes solo admite consulta. Las restricciones
por sede tambien se aplican al acceso directo por identificador.
El comprobante puede visualizarse e imprimirse desde su pantalla.

No se afirma cumplimiento de facturacion fiscal o electronica. No se inventan
impuestos, tasas, datos fiscales ni reglas de anulacion no acordadas.
HU25 aun requiere revisar su alcance documental restante, incluido el
conflicto entre el backlog y su historia individual sobre impuestos y envio
por correo. HU24 (tarjetas) y HU26 (historial) siguen pendientes.

## API y datos

- POST /api/payments/cash/: order, received_amount, expected_total,
  idempotency_key. Devuelve payment e invoice; 201 al crear, 200 al repetir.
- GET /api/invoices/{id}/: consulta protegida del comprobante.
- El detalle de pedido PAID ofrece el enlace al comprobante solo a los roles
  autorizados. El total historico no se sustituye por precios actuales.
- Nuevas tablas Payment, Invoice e InvoiceCounter en apps.payments.
- Migraciones: payments.0001, orders.0005 y audit.0020.
- Se respaldo la base local en backups antes de aplicar las migraciones.
- No se cobraron pedidos reales durante las pruebas ni se crearon datos QA
  en la base de presentacion. Pagos, comprobantes y contadores siguen vacios.
- La huella SHA-256 de los registros operativos antes y despues coincide:
  f887411da96e269a51e8c2f0e66da2f4218f94509983d384dbf97d188a7771fd.

## Verificacion

- 328 pruebas de regresion aprobadas inicialmente en SQLite temporal.
- 330 pruebas aprobadas en un MySQL 8 temporal independiente, incluidas las
  dos de concurrencia. Se comprobo una sola transaccion ante confirmaciones
  simultaneas con referencia igual o distinta.
- 43 pruebas de navegador aprobadas; un caso duplicado de anchos omitido.
  Los pagos del navegador se interceptan: no llegan al servidor de presentacion.
- Formulario y comprobante revisados visualmente en escritorio y movil.
- Compilacion correcta; no hay migraciones faltantes por generar.
- El contenedor MySQL temporal se retira al finalizar.

Siguiente historia: HU24, registro de pagos con tarjeta, revisando antes sus
criterios y manteniendo la generacion atomica del comprobante.

## Integracion posterior con HU24

El 25 de octubre de 2026 se incorpora la alternativa Pay by card.
Ambos metodos comparten la misma transaccion y proteccion de pago unico
por pedido. Los comprobantes en efectivo existentes conservan su contenido.
