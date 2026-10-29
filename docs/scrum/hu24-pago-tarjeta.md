# HU24 - Registro de tarjeta de credito o debito

Entrega local del 25 de octubre de 2026.

## Alcance

El cajero procesa el cargo en un datafono externo. El aplicativo solo
registra la aprobacion manual; no autoriza ni ejecuta cargos bancarios.
No hay pasarela, conexion bancaria ni almacenamiento de numeros de tarjeta
o codigos de seguridad.

1. Cashier o Administrator abre un pedido IN_CASHIER.
2. Pay by card abre el formulario de registro.
3. Selecciona Credit card o Debit card, e ingresa Approval reference.
4. Confirma expresamente que el pago fue aprobado en el terminal externo.
5. Confirm card payment registra el metodo, genera el comprobante interno,
   cambia el pedido a PAID y libera la mesa, en una misma transaccion.

Al cambiar el tipo o referencia se desmarca la aprobacion. Tras recargar la
pagina, es necesario confirmar de nuevo: la casilla no se guarda marcada.

## Datos y validacion

- Metodos: CASH, CREDIT_CARD y DEBIT_CARD. No se admiten pagos mixtos.
- La referencia admite de 3 a 40 caracteres ASCII: letras, numeros, punto,
  guion, guion bajo y barra. Se normaliza a mayusculas y sin espacios externos.
- Se rechazan secuencias de 13 o mas digitos, incluso agrupados con separadores,
  que podrian corresponder a un numero de tarjeta. Se debe utilizar una
  referencia de aprobacion adecuada, no un PAN.
- El formulario no pide numero de tarjeta, titular, caducidad, PIN o CVV.
- La API de tarjeta rechaza campos adicionales, incluidos los de efectivo
  o datos sensibles, sin copiarlos al comprobante ni a la auditoria.
- Se requieren terminal_approved y expected_total. El servidor verifica
  rol, sede, estado, total de los items e integridad de la mesa.
- En tarjeta se registra el total exacto, sin cambio. received_amount
  mantiene por compatibilidad ese mismo total; no representa efectivo recibido.
- El comprobante muestra el tipo y la referencia; oculta los campos de
  efectivo recibido y cambio. Los comprobantes antiguos CASH siguen legibles.
- El metodo y la referencia constan en PAYMENT_PROCESSED y en la copia
  inmutable de datos del comprobante.

## Integridad y reintentos

Efectivo y tarjeta comparten la transaccion, bloqueos, numeracion por sede,
auditoria y la restriccion de un unico pago por pedido.

La referencia UUID de reintento no es la referencia de aprobacion del datafono.
Es unica por intento. Un reintento conserva pedido, cajero, tipo, total y
referencia; devuelve el mismo pago sin volver a registrarlo. Cambiar los datos
de un pago ya confirmado devuelve conflicto.

Si falla el comprobante o la auditoria se revierte todo. No se vuelve a
descontar inventario al registrar la tarjeta. Un intento en efectivo no puede
seguir a tarjeta, ni a la inversa, aunque se presenten simultaneamente.

El tipo, aprobacion y datos monetarios tambien tienen una restriccion de
consistencia en la base. Los metodos desconocidos y combinaciones de efectivo
con metadatos de tarjeta no cumplen esa restriccion.

## Implementacion

- POST /api/payments/card/: order, expected_total, method,
  approval_reference, terminal_approved e idempotency_key.
- 201 para registro nuevo; 200 al repetir el mismo pago; 409 para conflicto.
- Migracion payments.0002: referencia, confirmacion y metodos admitidos.
- Se respalda MySQL antes de migrar y se conserva la huella de registros
  operativos, pagos y comprobantes previos. Las nuevas columnas de efectivo
  reciben valores neutros; no se reescribe el comprobante historico.
- Pruebas de navegador con respuestas interceptadas, nunca con cargos o
  registros de tarjeta sobre pedidos de presentacion.
- Pruebas del servidor y concurrencia en una base MySQL temporal independiente.

## Verificacion final (2026-10-25)

- 352 pruebas de backend aprobadas en MySQL aislado, incluidas cinco de
  concurrencia. El contenedor temporal fue eliminado al terminar.
- 53 pruebas de interfaz aprobadas en escritorio y movil; una comprobacion
  duplicada de dimensiones se omite intencionalmente.
- Compilacion Vite correcta, sin migraciones adicionales pendientes y
  revision visual de formulario y comprobante en escritorio y movil.
- Se corrigio el foco inicial del formulario para situarlo en la referencia.
- Respaldo previo: backups/antes-hu24-2026-10-25-card.sql.
- Se conserva el pago en efectivo existente y su comprobante. No se crearon
  pagos de tarjeta en los datos de presentacion mediante las pruebas.
- Huella operativa antes y despues de la migracion:
  cf6edd2ae01ffb5384381dae1f5d3483c2614f139c88ac769703ff44fc308fce.

## Siguiente etapa

HU25 completa el panel y HU26 agrega el filtrado del historial, conservando el
comprobante interno existente. Esta entrega no agrega facturacion electronica,
impuestos, integracion bancaria ni reembolsos.
