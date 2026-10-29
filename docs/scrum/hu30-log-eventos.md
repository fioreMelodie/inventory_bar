# HU30 - Consulta del log de eventos

Fecha: 2026-10-25.

## Alcance

Nuevo Audit > Event log, solo para Administrator, en /audit/events.
Consulta y detalle, sin edicion, eliminacion, exportacion ni graficas.
El registro existente se conserva desde su inicio, sin limite de antiguedad.

Filtros opcionales y combinables con AND: rango de fechas, nombre de usuario
(coincidencia parcial sin distinguir mayusculas), tipo de evento y sede.
Las sedes inactivas se incluyen en las opciones. Las fechas usan dias
completos de America/Bogota y se valida el orden del rango. HU29 exige fechas
en reportes de ventas, no en esta consulta de auditoria.

Tabla con fecha/hora, usuario, tipo, entidad/ID y sede. Orden descendente por
fecha e ID, paginacion de 25 eventos, filtros en URL y estados vacio/error.
El detalle agrega descripcion, IP y el timestamp original completo, sin
truncar la precision registrada. Hora legible en Bogota e ISO original.

## Contexto de sede y conservacion

El modelo anterior no almacenaba sede. audit.0021 agrega venue, venue_name
y venue_recorded, sin reescribir los campos originales de ningun evento.
Los anteriores quedan con contexto desconocido: Not recorded.

Los nuevos eventos guardan la sede y su nombre en el momento del evento:
- Pedidos, inventario, pagos, comprobantes y mesas: sede de la operacion.
- Cambios de usuarios: sede del usuario afectado, no la del administrador.
- Cambios de sedes: la sede afectada.
- Inicio/cierre de sesion: la sede guardada en la sesion; no cambia si se
  reasigna despues la cuenta.
- Eventos globales o sin vinculacion, incluidos intentos sin cuenta asociada:
  Not associated. Esto es distinto de no haber guardado contexto historico.

No se deducen sedes antiguas del usuario actual ni se interpreta texto libre
para asignarlas. Los filtros de sede no pueden clasificar esos registros:
siguen disponibles en All venues y en Not recorded. Reconstruir su sede
requiere una fuente verificable y una decision posterior.

Los tipos existentes cubren autenticacion, cierre de sesion, usuarios,
catalogo, proveedores, inventario, pedidos, pagos, comprobantes y cambios de
configuracion de sedes/mesas/catalogo/usuarios. No se agrega una pantalla
de configuracion nueva ni un sistema para auditar ediciones externas de archivos.

## API y seguridad

- GET /api/audit/events/: listado paginado y tipos de evento disponibles.
- GET /api/audit/events/<id>/: detalle de solo lectura.
- Parametros: start_date, end_date, username, event_type, venue y page.
- venue=__unrecorded__: contexto historico no registrado.
- venue=__none__: eventos nuevos sin vinculacion a una sede.
- Cashier y Waiter reciben 403; sin autenticar, 401. Los IDs conocidos no
  permiten eludir los permisos. No se admiten POST/PUT/PATCH/DELETE.
- Cache-Control: no-store. El listado no descarga descripciones ni IP;
  el detalle las consulta solo bajo los mismos permisos de administrador.
- La interfaz representa las descripciones como texto, no HTML ejecutable.
- Modelos, operaciones masivas y Django admin conservan las restricciones
  de inmutabilidad. Django admin exige rol Administrator tambien para ver.

## Validacion y respaldo

Respaldo previo: backups/antes-hu30-2026-10-25.sql, privado e ignorado por Git.
La migracion incorpora indices por fecha/ID y sede/fecha/ID.
Prueba aislada con 5000 eventos: filtros combinados, pagina de 25 registros,
dos consultas SQL (conteo y pagina) y exigencia de menos de dos segundos.
Medicion adicional en navegador contra los datos locales. Los tiempos solo
describen el entorno y volumen medidos, no cualquier servidor o red.

Huella de los campos originales del log previo: 1656 eventos, hasta ID 1656,
de02d1be33ac26e3524d70b12446231d7d5ae1c31361c002161543e96bdcc7b2.
Se comprueba de nuevo ese mismo prefijo despues de las pruebas. Nuevos
inicios/cierres de sesion pueden agregar eventos; no se elimina ninguno.

Huella operativa previa:
7e61875f341190145cac17451d29cf5f77cc0f21d9a11e32d92edd1111448ddf.

## Resultados de cierre

- 413 pruebas de backend aprobadas en MySQL aislado, incluidas las cinco
  de concurrencia. Contenedor y base temporal eliminados al terminar.
- Suite completa de interfaz: 103 aprobadas y una comprobacion duplicada
  de dimensiones omitida intencionalmente. Las diez especificas de HU30
  aprobaron de nuevo tras el ajuste visual de filtros y detalle en movil.
- MySQL: consulta filtrada de 5000 eventos, 25 filas por pagina, dos
  consultas SQL, 0.005 s. Navegador final: 42 ms escritorio y 44 ms movil
  desde navegacion hasta eventos visibles, sobre los datos locales reales.
- Capturas revisadas a 320, 390, 768 y 1440 pixeles; detalle de evento en
  escritorio y movil. Se conserva el cierre por Escape y retorno del foco.
- Verificada la misma huella de los campos originales de los 1656 eventos
  anteriores. Los registros nuevos de inicio/cierre de sesion se agregan
  normalmente, sin modificar el prefijo conservado.
- Huella operativa final identica a la previa. No se crearon pagos ni se
  modificaron inventario, pedidos o cuentas en la base de presentacion.
- Migracion audit.0021 aplicada tras respaldo privado; sin migraciones
  adicionales pendientes. Compilacion Vite y git diff --check correctos.
- Despliegue solo local en http://127.0.0.1:8088/audit/events; sin commit ni push.

HU30 queda disponible con la limitacion explicita del contexto de sede
anterior ausente; esos eventos se conservan completos y visibles.
