# Sprint 2 — Catálogo, Proveedores e Inventario

| Campo | Valor |
| ----- | ----- |
| Fechas | 07 — 20 de septiembre de 2026 |
| Duración | 2 semanas |
| Story Points | 27 SP |
| Historias | HU09 · HU10 · HU11 · HU12 · HU13 · HU14 · HU15 |

## Sprint Goal

Dejar operativo el catálogo global de productos, el directorio de proveedores y el control de
inventario por sede, de modo que el Sprint 3 pueda construir mesas y pedidos sobre una base de
productos y existencias ya funcional.

## Sprint Backlog

| ID | Historia de Usuario | Módulo | Prioridad | SP | Rama |
| -- | ------------------- | ------ | --------- | -- | ---- |
| HU09 | Crear producto en el catálogo | Catálogo de Productos | Alta | 5 | `feature/HU-09-crear-producto` |
| HU10 | Editar producto del catálogo | Catálogo de Productos | Alta | 3 | `feature/HU-10-editar-producto` |
| HU11 | Consultar catálogo de productos | Catálogo de Productos | Alta | 3 | `feature/HU-11-consultar-catalogo` |
| HU12 | Registrar proveedor | Gestión de Proveedores | Media | 3 | `feature/HU-12-registrar-proveedor` |
| HU13 | Asociar proveedor a productos | Gestión de Proveedores | Media | 5 | `feature/HU-13-asociar-proveedor` |
| HU14 | Registrar entrada de mercancía | Inventario | Alta | 5 | `feature/HU-14-registrar-entrada-inventario` |
| HU15 | Consultar stock disponible por sede | Inventario | Alta | 3 | `feature/HU-15-consultar-stock` |

## Entregables semanales

- **Semana 1 (07 — 13 sep):** HU09 · HU10 · HU11 — 11 SP
- **Semana 2 (14 — 20 sep):** HU12 · HU13 · HU14 · HU15 — 16 SP

## Sprint Review

| Campo | Valor |
| ----- | ----- |
| Story Points comprometidos | 27 SP |
| Story Points completados | 27 SP |
| Historias aceptadas | 7 de 7 |
| Pruebas automatizadas | 175 en total, todas en verde |

### Incremento entregado

- Catálogo global de productos con imagen opcional, compartido por todas las sedes y con
  precios uniformes. Creación, edición e inactivación reservadas al Administrador; consulta
  disponible para los tres roles con filtros por tipo, categoría y nombre.
- El valor de compra es visible únicamente para el Administrador; Cajero y Mesero solo ven el
  valor de venta.
- Directorio de proveedores con asociación de productos. Un producto tiene un proveedor
  principal; un proveedor puede suministrar varios productos.
- Inventario por sede: registro de entradas de mercancía y consulta de existencias, con
  resaltado de productos agotados y alcance por rol.

## Decisiones técnicas del sprint

1. **Precios como enteros.** El valor de compra y el de venta se almacenan como enteros
   positivos, en pesos colombianos sin decimales, conforme al criterio de la HU09 de que los
   valores sean numéricos enteros.
2. **El stock se consulta sobre el catálogo, no sobre los registros de existencias.** Un
   producto sin entradas no tiene fila en la tabla de stock; si el listado se construyera sobre
   esa tabla, los productos nunca recibidos desaparecerían. Se consulta el catálogo activo y se
   informa cantidad cero, que es justo lo que la HU15 pide resaltar.
3. **Incremento de stock con `F()`.** Dos cajeros registrando entradas del mismo producto a la
   vez perderían uno de los dos incrementos si se leyera y escribiera en pasos separados.
4. **Movimientos de inventario desde el inicio.** Aunque ninguna historia del Sprint 2 los
   exige explícitamente, cada variación del stock genera un registro `StockMovement`. La HU16 y
   el módulo de reportes del Sprint 5 lo necesitan, y reconstruirlo después sería imposible
   para los movimientos ya ocurridos.
5. **Asociación proveedor-producto por lista completa.** El endpoint recibe la lista total de
   productos del proveedor en lugar de altas y bajas individuales: asociar, modificar y
   eliminar la relación se resuelve en una sola operación atómica, y la reasignación a otro
   proveedor queda garantizada sin estados intermedios inconsistentes.

## Retrospectiva — Start / Stop / Continue

**Start**
- Anticipar las estructuras que necesitan las historias posteriores cuando el costo de
  incorporarlas es bajo y el de reconstruirlas es alto, como ocurrió con los movimientos de
  inventario.

**Stop**
- Declarar campos de serializador que dependen de relaciones aún inexistentes. En la HU12 se
  incluyó un contador de productos antes de que existiera la relación proveedor-producto;
  Django REST Framework lo omitía en silencio en lugar de fallar, lo que habría pasado
  inadvertido hasta la HU13. Se retiró y se incorporó en la historia correspondiente.

**Continue**
- Una prueba automatizada por criterio de aceptación, incluidas las reglas negativas: que un
  Mesero no pueda registrar inventario o que un Cajero no vea otra sede está verificado, no
  supuesto.

## Preparación del Sprint 3

El Sprint 3 (21 sep — 04 oct) aborda mesas y pedidos: HU16 a HU21, 26 SP. Queda disponible lo
que necesitan: catálogo de productos activo, existencias por sede y el servicio de inventario
donde se apoyará el descuento automático de stock de la HU16.
