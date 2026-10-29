# Mejora de experiencia de usuario

Revision local del 23 de octubre de 2026. No se publica al repositorio remoto.

## Alcance

- Navegacion lateral por rol, agrupada en Operations y Management.
- Menu modal para movil, indicador de conexion y ubicacion de la pantalla.
- Inicio operativo: pedidos activos, ocupacion de mesas, pedidos pendientes
  de pago, importe pendiente y productos activos. Datos obtenidos de la API,
  sin indicadores de ventas ni cifras simuladas.
- Resumen por sede y enlaces a los pedidos existentes.
- Sala con estados diferenciados, resumen y acciones de altura estable.
- Busqueda de usuarios por nombre, usuario o sede, y filtro por rol.
- Nueva pantalla de acceso con control de visibilidad de contrasena.
- Tipografia, controles, tablas, colores y espaciados compartidos.
- Dialogos nativos con foco contenido, restauracion de foco y confirmacion
  segura. La perdida de conexion sigue requiriendo confirmacion explicita.
- Navegacion por teclado, enlace para saltar al contenido y respeto de la
  preferencia de movimiento reducido.

No se cambian permisos, contrasenas, reglas de inventario, precios ni el
cierre por inactividad de tres minutos. La pantalla de caja conserva su
consulta automatica de pedidos, identificada como actividad de fondo.

La imagen del acceso es una ilustracion fotografica generada, no una foto
de una sede real. Se incluye en frontend/public/images/cafe-interior.png.

## Verificacion

La compilacion se realiza con npm run build. Las pruebas de navegador estan
en frontend/tests/interface.spec.js y se ejecutan desde frontend con:

    npm run test:ui

Requieren Google Chrome, la aplicacion local iniciada y las variables
UI_ADMIN_PASSWORD, UI_WAITER_PASSWORD y UI_CASHIER_PASSWORD configuradas
en el entorno. UI_BASE_URL permite cambiar la direccion de la aplicacion.
Las claves no se incluyen en los archivos de pruebas.

Las pruebas cubren escritorio y movil, anchos adicionales de 320, 768, 1024
y 1920 pixeles, navegacion, roles, filtros, estados vacios, errores, acceso,
dialogos, conexion, listas desplegables y validacion de precios.
No crean, editan ni eliminan datos operativos. Las pruebas de conexion y
acceso generan los eventos normales de auditoria de sesiones.
Las capturas quedan en frontend/test-results, excluido de Git y Docker.
Resultado de la revision: 21 pruebas aprobadas. La comprobacion adicional
de anchos se ejecuta una vez en escritorio; su duplicado movil se omite.

## Pendiente independiente

npm audit reporta nueve alertas en el conjunto de dependencias. La consulta
sin dependencias de desarrollo reporta tres: follow-redirects (una alta)
y react-router/react-router-dom (dos moderadas). No se aplican actualizaciones
mayores automaticas como parte del cambio visual. Esto requiere una revision
separada de dependencias; no equivale a comprobar explotabilidad en la app.
