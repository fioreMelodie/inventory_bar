# Ajustes solicitados en la revision del docente

## Precio de venta frente al precio de compra

Solicitud confirmada el 23 de octubre de 2026:
no permitir registrar un precio de venta menor al precio de compra.

- Regla: sale_price >= purchase_price. Se permite que los dos precios sean iguales.
- Se aplica al crear y editar productos desde el catalogo y su API.
- Las ediciones parciales comparan el precio enviado con el precio vigente
  que no se haya modificado. Si se cambian ambos, se comparan los dos nuevos.
- El formulario informa el error antes de enviar; la API tambien lo rechaza
  con HTTP 400 y un error asociado a sale_price.
- Mensaje de interfaz: Sale price cannot be lower than purchase price.
- Una solicitud rechazada no guarda el producto ni registra una creacion
  o modificacion exitosa en la auditoria.

No se modifican automaticamente precios existentes ni precios congelados en
los pedidos historicos.

## Seleccion de tipo y categoria

Los campos Type y Category del formulario de creacion y edicion de productos
se cambian a listas desplegables; no admiten texto libre desde la interfaz.
Ambos requieren una seleccion antes de guardar.

Las opciones iniciales se toman del catalogo de demostracion existente:
tipos Beverage y Food; categorias Beer, Liquor, Soft Drink, Water, Coffee
y Snacks. Se incluyen ademas los valores del listado de productos cargado y
los valores del producto en edicion, para conservar la informacion previa.
Las opciones base permiten registrar productos incluso con un catalogo vacio.

Este ajuste cambia los controles de la interfaz; no redefine la clasificacion
de los productos existentes ni restringe los valores aceptados por la API.

## Preparacion de datos para la presentacion

Se conservan los datos actuales y se retiran los registros operativos con
prefijo QA. Se respaldo MySQL antes de la limpieza en la carpeta local backups,
excluida de Git. El historial de auditoria se conserva.

Se retiraron cuatro productos QA y una mesa QA con su pedido. Se revirtio el
descuento de inventario de ese pedido de prueba, conservando los demas datos.

Se configuraron las cuentas admin (administrator), waiter y cashier. Los dos
roles operativos se asignaron a Galeria. Las contrasenas se almacenan mediante
hash en la base de datos y no se incluyen en esta documentacion.
La cuenta administradora QA se renombro para conservar sus referencias.
Los usuarios anteriores sin prefijo QA permanecen disponibles.

## Idioma de la aplicacion

La interfaz, los mensajes de validacion, las etiquetas de roles y estados,
el panel de Django y los nuevos eventos de auditoria se muestran en ingles.
Las cuentas mesero y cajero se renombran a waiter y cashier, conservando
sus identificadores, contrasenas, permisos, sede y referencias historicas.
Los nombres visibles de estas cuentas son Waiter y Cashier; admin se muestra
como Administrator.

Los nombres propios de sedes, productos y proveedores no se traducen.
La auditoria historica no se reescribe. La documentacion y los comentarios
del codigo pueden permanecer en espanol.
