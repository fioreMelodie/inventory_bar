# Validacion de HU01 a HU21

Fecha: 8 de octubre de 2026.

## Entorno y alcance

Backend ejecutado con `backend/.venv/bin/python`, Django 5.2.6 y SQLite.
Las pruebas de Django usan su base temporal. La verificacion del navegador usa
una base exclusiva de QA fuera del repositorio y tres cuentas ficticias.
No se ejecutaron migraciones ni cargas de datos sobre `backend/db.sqlite3`.

La validacion combina pruebas de API y reglas de negocio, compilacion del
frontend y recorridos de Chrome mediante Playwright. Se consultaron los
criterios de las historias disponibles en `docs/historias de usuario`.

## Resultado por historia

Los conteos corresponden a las pruebas preexistentes de cada HU; las pruebas
de renovacion y las regresiones compartidas se contabilizan por separado.

| HU | Funcionalidad | Pruebas de backend | Resultado |
| --- | --- | ---: | --- |
| HU01 | Login y permisos iniciales | 10 | Aprobadas |
| HU02 | Inactividad | 8 | Aprobadas |
| HU03 | Cierre manual y desconexion | 8 | Aprobadas |
| HU04 | Crear sede | 10 | Aprobadas |
| HU05 | Editar e inactivar sede | 15 | Aprobadas |
| HU06 | Crear usuario | 15 | Aprobadas |
| HU07 | Editar usuario | 14 | Aprobadas |
| HU08 | Inactivar y reactivar usuario | 12 | Aprobadas |
| HU09 | Crear producto | 11 | Aprobadas |
| HU10 | Editar producto | 11 | Aprobadas |
| HU11 | Consultar catalogo | 12 | Aprobadas |
| HU12 | Gestionar proveedores | 12 | Aprobadas |
| HU13 | Asociar productos y proveedores | 12 | Aprobadas |
| HU14 | Registrar entrada de inventario | 13 | Aprobadas |
| HU15 | Consultar stock | 12 | Aprobadas |
| HU16 | Descontar y reintegrar stock | 15 | Aprobadas |
| HU17 | Configurar mesas | 14 | Aprobadas |
| HU18 | Consultar sala | 12 | Aprobadas |
| HU19 | Abrir pedido | 14 | Aprobadas |
| HU20 | Agregar productos | 14 | Aprobadas |
| HU21 | Enviar a caja | 12 | Aprobadas |

Resultado total: 274 pruebas aprobadas, incluidas 9 pruebas existentes de
renovacion de tokens y 9 regresiones nuevas. La suite inicial tenia 265 pruebas.
Seis regresiones nuevas fallaron antes de aplicar las correcciones.

Frontend: `npm run build` aprobado. Chrome: 27 comprobaciones aprobadas,
incluidas verificaciones repetidas de login y comprobaciones del montaje de
datos. Sin errores JavaScript no capturados. Se inspeccionaron capturas a
1280 x 900 y 390 x 844; el menu de administrador tambien se comprobo a 390 px.

## Correcciones realizadas

- HU07: los permisos autenticados toman el rol y la sede guardados en la
  sesion. Los cambios de la cuenta aplican al siguiente login.
- HU02: las consultas automaticas y sus renovaciones de token no reinician
  el contador del servidor. La interaccion real notifica actividad, el
  temporizador sobrevive a la navegacion interna y el cierre local es inmediato.
- HU03: el aviso persiste aunque vuelva la conexion. Se limita el tiempo de
  sondeo, y los cierres pendientes se reenvian al servidor al recuperar acceso
  para invalidar la sesion y registrar su causa.
- Listados: catalogo, usuarios, sedes, proveedores, mesas y pedidos recuperan
  todas las paginas. Los registros posteriores al numero 25 son accesibles.
- HU15: inventario se actualiza automaticamente cada 10 segundos, permite
  filtrar por categoria y muestra errores de consulta.
- HU18/HU21: la sala conserva el pedido y el tiempo de ocupacion despues del
  envio a caja. La consulta individual de mesas respeta la sede de cada rol.
- HU19: se rechazan pedidos nuevos en sedes inactivas y se vuelve a validar
  la mesa dentro de la transaccion despues de bloquear su fila.
- HU16/HU20: cancelar exige el propietario o un administrador. Se agrego
  confirmacion de cancelacion en la interfaz, se corrigio la cantidad inicial
  vacia y se serializan las modificaciones del pedido en el backend.
- HU10/HU11: un rol operativo no puede consultar por ID un producto inactivo.
- HU21: el inicio del cajero muestra pedidos pendientes y consulta cambios
  cada 5 segundos. Los pedidos enviados se consultan en modo lectura.
- Interfaz: menu adaptable al ancho movil, cabecera del pedido con salto de
  linea y etiquetas de estado del pedido en ingles.
- Configuracion: se admite una ruta SQLite aislada mediante `DB_SQLITE_PATH`
  y un backend alternativo de Vite mediante `API_PROXY_TARGET`.

## Repetir las pruebas

Desde `backend`:

```sh
.venv/bin/python manage.py test --noinput
.venv/bin/python manage.py makemigrations --check --dry-run
```

Desde `frontend`:

```sh
npm run build
```

Para repetir Chrome, crear una base SQLite nueva cuyo nombre comience por
`bar-inventory-qa-`. El script de carga rechaza otras bases y requiere una base
vacia. No usar la base habitual del proyecto.

Desde `backend`, usando la misma ruta para los tres comandos:

```sh
DB_ENGINE=sqlite DB_SQLITE_PATH=/private/tmp/bar-inventory-qa-example .venv/bin/python manage.py migrate --noinput
DB_ENGINE=sqlite DB_SQLITE_PATH=/private/tmp/bar-inventory-qa-example .venv/bin/python manage.py shell < scripts/seed_qa.py
DB_ENGINE=sqlite DB_SQLITE_PATH=/private/tmp/bar-inventory-qa-example .venv/bin/python manage.py runserver 127.0.0.1:8001 --noreload
```

Desde `frontend`, en otra terminal:

```sh
API_PROXY_TARGET=http://127.0.0.1:8001 npm run dev -- --host 127.0.0.1 --port 5174 --strictPort
```

El recorrido requiere Playwright y Chrome. Desde `frontend`:

```sh
node scripts/verify-workflows.mjs
```

Si Playwright no esta instalado en el proyecto, `PLAYWRIGHT_MODULE` puede
apuntar a una instalacion disponible. `QA_BASE_URL` permite cambiar la URL.
El recorrido modifica exclusivamente los datos de la instancia donde se
autentican las cuentas de QA; verificar su URL antes de ejecutarlo.

Datos ficticios: `qa_admin`, `qa_cashier` y `qa_waiter`, con contrasena
`QaPassword2026*`. La carga crea 30 productos con stock de 10 y 30 mesas.
El recorrido agrega mercancia y registra pedidos; para repetirlo se necesita
otra base vacia y una nueva carga.

## Limites de esta validacion

Las pruebas aprobadas respaldan los casos cubiertos, no certifican cada
criterio del documento ni equivalen a aceptacion final del cliente.
Los recorridos de navegador se centran en login, catalogo, mesas, inventario,
pedidos y sesiones; no sustituyen una revision manual de todos los formularios
administrativos ni una auditoria completa de accesibilidad.

No se ejecutaron pruebas sobre MySQL, pruebas de carga ni transacciones
simultaneas reales. SQLite no permite verificar el comportamiento de los
bloqueos de fila de MySQL. Debe validarse esa configuracion antes de desplegar.

HU22 a HU30 no forman parte de esta ejecucion. No se implementaron cobros,
facturas ni reportes. El listado de pendientes del cajero se agrego para
completar la visibilidad requerida por HU21.
