# Decisiones de requisitos

Acuerdos confirmados con el responsable del proyecto el 23 de octubre de 2026.
Estos acuerdos resuelven los puntos indicados donde el backlog general y las
historias individuales difieren. No cierran las demas diferencias documentales.

| Tema | Regla acordada |
| --- | --- |
| Inactividad | Cierre de sesion tras 3 minutos sin interaccion. Cada interaccion reinicia el contador. |
| Proveedores | Cada producto admite un unico proveedor principal. Se conserva la asociacion opcional actual. |
| Inventario | Se descuenta al agregar cada producto al pedido. Se reintegra al cancelar el pedido abierto. |
| Mesas | Solo se almacenan los estados FREE y OCCUPIED. |
| Pendiente de pago | Es una etiqueta visual derivada del pedido IN_CASHIER; no es un tercer estado de la mesa. |

La vista de sala muestra Occupied y Pending payment cuando el pedido activo
esta en caja. Un pedido abierto muestra Occupied sin esa etiqueta; una mesa
libre muestra Free. El idioma de la interfaz se mantiene en ingles.

El estado del pedido se obtiene de la API de sala mediante active_order_status,
sin guardar informacion duplicada en la mesa ni hacer consultas extra por mesa.
La etiqueta se actualiza con el sondeo de sala existente, cada 10 segundos.

Actualizacion del 25 de octubre de 2026: HU23 incorpora el pago en efectivo.
Al confirmar el pago, el pedido pasa a PAID, la mesa queda FREE y se genera
un comprobante interno inmutable, dentro de una misma transaccion.
El stock no vuelve a descontarse al cobrar.
HU24 incorpora el registro manual de tarjeta de credito o debito aprobada
en un datafono externo. Requiere referencia y confirmacion explicita; no
integra una pasarela ni ejecuta el cargo bancario. Un pedido admite un solo
pago, sin dividirlo entre efectivo y tarjeta.
HU25 completa el panel de consulta de comprobantes: generacion automatica,
numeracion por sede, visualizacion e impresion y acceso por rol/sede.
Se mantiene el alcance de comprobante interno; no se declara cumplimiento
de facturacion fiscal o electronica. No se permite editar ni anular.
HU26 agrega al mismo panel filtros combinados por fechas, numero y sede.
Los dias se interpretan en America/Bogota y sin filtros no se limita la
antiguedad del historial. Se mantienen los permisos y la inmutabilidad.

HU29: reglas confirmadas por el responsable el 25 de octubre de 2026.
Los reportes de ventas de Administrator y Cashier requieren ambas fechas,
sin rango preseleccionado ni consulta automatica sin fechas. Esto sustituye
la consulta sin fechas de HU27/HU28, no la del historial de comprobantes HU26.
No hay limite de antiguedad dentro del rango elegido. Categoria sigue siendo
exclusiva de Administrator; Cashier mantiene solo fechas y producto, con sede
fija y sin costos o ganancias, de acuerdo con HU28.
