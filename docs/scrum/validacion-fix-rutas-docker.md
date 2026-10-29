# Validacion del fix de rutas en Docker

Fecha: 23 de octubre de 2026.
Base: pkmilo, commit 9c5e78b, con el fix aplicado en trabajo-local.

## Cambio

Las rutas /admin/... pertenecen a React. El panel propio de Django se sirve
en /django-admin/. Nginx envia /api y /django-admin al backend y conserva
el fallback de React para las pantallas de la aplicacion.

## Entorno verificado

- Proyecto Compose separado: bar_inventory_fix_qa.
- MySQL 8, Django 5.2.6 con Gunicorn y frontend compilado servido por Nginx.
- Puerto publicado exclusivamente en 127.0.0.1:8088.
- Volumen MySQL nuevo, con base bar_inventory_qa y datos ficticios.
- Configuracion local en .env, excluida de Git.
- No se modificaron los datos de la copia anterior ni se publicaron cambios.

## Resultados

Nginx aprobo la validacion de sintaxis. El backend aplico las migraciones,
incluida orders.0003_mysql_unique_open_order, y recopilo los archivos estaticos.
Se creo un administrador de QA y se ejecuto seed_demo.

Chrome con Playwright aprobo 13 comprobaciones:

- Login del administrador de React a traves de Nginx.
- Apertura directa y recarga de /admin/users, /admin/venues,
  /admin/suppliers y /admin/tables: ocho comprobaciones, todas con HTTP 200
  y la pantalla React correspondiente, sin redireccion al panel de Django.
- Respuesta JSON del endpoint /api/health/.
- Login y acceso al panel separado en /django-admin/.
- Entrega de la hoja de estilos del panel Django por Nginx.
- Ausencia de errores JavaScript no capturados.

Se inspeccionaron capturas de las pantallas de React y Django.
La suite de 277 pruebas aprobada previamente corresponde a SQLite.
Esta validacion no equivale a ejecutar toda esa suite en MySQL ni a probar
concurrencia; verifica el arranque y el fix de rutas sobre el despliegue real.

## Repetir manualmente

Con esta instancia activa, abrir http://127.0.0.1:8088/login e iniciar sesion
con una cuenta administradora. Visitar Usuarios, Sedes, Proveedores y Mesas,
recargando cada pantalla y abriendo sus enlaces directamente.
Abrir http://127.0.0.1:8088/django-admin/ y comprobar su acceso separado.
