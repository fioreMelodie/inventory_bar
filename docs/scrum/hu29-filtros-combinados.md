# HU29 - Filtros combinados en reportes de ventas

Fecha: 2026-10-25.

## Reglas confirmadas

El responsable confirma que ambos extremos del rango son obligatorios para
los dos reportes y que categoria queda solo para Administrator. Se mantienen
el alcance y las restricciones de HU27/HU28. No se agregan graficas.

- Administrator: fechas obligatorias; sede, producto y categoria opcionales.
- Cashier: fechas obligatorias y producto opcional; sede fija, sin categoria,
  costos, ganancias ni acceso a exportaciones del administrador.
- Todos los criterios se aplican con AND. Se mantiene la coincidencia de
  producto por ID o nombre parcial, segun las historias anteriores.
- No se consulta un reporte hasta tener ambas fechas. Clear filters retira
  los resultados y limpia el rango; no solicita un reporte global sin fechas.
- La API rechaza fechas ausentes, vacias, invalidas o invertidas con 400,
  tambien en las salidas CSV/impresion del administrador.
- No se impone limite de antiguedad al rango elegido. HU26 conserva fechas
  opcionales en el historial de comprobantes, que es un flujo diferente.
- Resultados por fecha descendente, con desempate estable por ID descendente.
- Sin coincidencias: No records found for the selected filters.
- Filtros, totales y permisos se conservan al cambiar pagina o recargar.
- Categorias de catalogo disponibles antes de generar el primer reporte;
  las historicas conocidas se incorporan al consultar el rango.

## Rendimiento y preservacion

payments.0003 agrega indices por (issued_at, id) y (venue, issued_at, id).
No modifica pagos ni snapshots. Se respalda la base antes de migrar en
backups/antes-hu29-2026-10-25.sql, archivo privado e ignorado por Git.

La prueba de rendimiento usa una base temporal con 2001 lineas pagadas,
filtros combinados y dos paginas por rol; mide la solicitud y exige menos de
dos segundos y una consulta SQL por reporte. Tambien se mide en navegador
la navegacion hasta mostrar totales, contra datos locales, en ambos roles.
Estos resultados describen el entorno y volumen probados; no constituyen
una garantia de tiempo para cualquier volumen, servidor o red.

No se agrega cache de informacion financiera ni se inventan costos historicos.
Se conservan filtros y calculos sobre datos inmutables y el aislamiento de sedes.

Huella operativa coincidente antes y despues de validar HU29:
7e61875f341190145cac17451d29cf5f77cc0f21d9a11e32d92edd1111448ddf.

## Resultados de cierre

- 398 pruebas de backend aprobadas en MySQL aislado, incluidas las cinco
  de concurrencia. Contenedor y base temporal eliminados al terminar.
- Suite completa de interfaz: 93 aprobadas y una comprobacion duplicada de
  dimensiones omitida intencionalmente.
- MySQL, 2001 lineas pagadas, una consulta SQL: Administrator pagina 1,
  0.033 s; pagina 2, 0.032 s; Cashier paginas 1 y 2, 0.032 s cada una.
- Navegador, datos locales reales, navegacion hasta totales: escritorio
  Administrator 49 ms, Cashier 41 ms; movil Administrator 50 ms, Cashier 36 ms.
- Capturas del reporte revisadas en escritorio y movil; se mantienen las
  comprobaciones de dimensiones a 320, 390, 768 y 1440 pixeles.
- Migracion payments.0003 aplicada tras respaldo privado; sin migraciones
  adicionales pendientes. Compilacion Vite y git diff --check correctos.
- Datos operativos preservados y sin pagos creados por las pruebas en la
  base de presentacion. Se uso la nueva clave local de cashier al validar.
- Cambios desplegados solo en http://127.0.0.1:8088, sin commit ni push.
