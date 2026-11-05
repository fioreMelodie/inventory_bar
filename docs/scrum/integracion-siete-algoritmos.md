# Integración de siete algoritmos

## Propósito

Esta integración permite demostrar en el aplicativo los algoritmos revisados en
la asignatura usando una instantánea de datos reales del catálogo y de los
pagos. No sustituye los índices, filtros ni ordenamientos de MySQL/Django en
los flujos transaccionales: esas herramientas siguen siendo la opción adecuada
para grandes volúmenes de datos y concurrencia.

La demostración está disponible solo para el Administrador en **Algorithms**
(`GET /api/algorithms/overview/`). La sugerencia de cambio está disponible para
Administrador y Cajero en `GET /api/algorithms/change/` y aparece antes de
confirmar un pago en efectivo; es informativa y no modifica el valor pagado.

## Ubicación y uso

| # | Algoritmo | Implementación | Integración en el negocio | Complejidad |
|---|---|---|---|---|
| 1 | Bubble Sort | `backend/apps/algorithms/algorithms.py::bubble_sort` | Ordena alfabéticamente la instantánea del catálogo que se presenta en Algorithms. | O(n²) |
| 2 | Insertion Sort | `backend/apps/algorithms/algorithms.py::insertion_sort` | Ordena la misma instantánea por precio de compra. | O(n²) |
| 3 | Quick Sort | `backend/apps/algorithms/algorithms.py::quick_sort` | Ordena la misma instantánea por precio de venta. | O(n log n) promedio; O(n²) peor caso. |
| 4 | Búsqueda binaria | `backend/apps/algorithms/algorithms.py::binary_search` | Busca por nombre exacto sobre la salida ordenada de Bubble Sort. | O(log n) |
| 5 | Cambio voraz | `backend/apps/algorithms/algorithms.py::greedy_change` | Sugiere denominaciones colombianas para el cambio en el cuadro de pago en efectivo. | O(d log d), con d denominaciones. |
| 6 | Voraz lexicográfico | `backend/apps/algorithms/algorithms.py::lexicographically_greatest` | Construye la cadena mayor por extremos a partir del texto de consulta en Algorithms. | O(n²) en esta representación de cadenas. |
| 7 | Mochila 0/1 | `backend/apps/algorithms/algorithms.py::knapsack_01` y `inventory_knapsack` | Recomienda como máximo una unidad de cada producto activo, maximizando margen estimado sin exceder un presupuesto de reposición. | O(n × C) |

## Decisiones de integración

- La búsqueda binaria es el séptimo algoritmo añadido para complementar los
  seis ejercicios suministrados durante el curso y aprovechar un caso real de
  consulta de catálogo.
- La mochila expresa el presupuesto en bloques de COP 1,000. El costo de cada
  producto se redondea hacia arriba, por lo cual la recomendación nunca excede
  el presupuesto real. El resultado es una ayuda de análisis, no una orden de
  compra automática.
- El cambio voraz usa las denominaciones COP 100,000, 50,000, 20,000, 10,000,
  5,000, 2,000, 1,000, 500, 200, 100 y 50. Si una cantidad no puede formarse
  exactamente, la respuesta informa el remanente y no altera la transacción.
- Las funciones trabajan sobre copias y no mutan el catálogo, inventario,
  pedidos, pagos ni comprobantes.

## Pruebas

Las pruebas unitarias se encuentran en
`backend/apps/algorithms/tests.py`. Cubren los tres métodos de ordenamiento,
búsqueda binaria, ambas estrategias voraces y mochila 0/1. Se ejecutan con:

```bash
cd backend
DB_ENGINE=sqlite python manage.py test apps.algorithms --noinput
```

La interfaz administrativa está en
`frontend/src/pages/AlgorithmsPage.jsx`; la integración visible del cambio
voraz está en `frontend/src/components/CashPaymentDialog.jsx`.
