# Sprint Review y Retrospectiva — Sprint 1

| Campo | Valor |
| ----- | ----- |
| Sprint | 1 — Autenticación, Sedes y Usuarios |
| Fechas | 24 de agosto — 06 de septiembre de 2026 |
| Story Points comprometidos | 27 SP |
| Story Points completados | 27 SP |
| Historias aceptadas | 8 de 8 |

## Incremento entregado

Software funcionando con autenticación completa, control de sesiones, administración de sedes y
gestión de usuarios con control de acceso por rol.

| ID | Historia | SP | Estado |
| -- | -------- | -- | ------ |
| HU01 | Inicio de sesión con credenciales | 5 | Aceptada |
| HU02 | Cierre automático de sesión por inactividad | 3 | Aceptada |
| HU03 | Cierre de sesión manual y pérdida de conexión | 3 | Aceptada |
| HU04 | Crear sede | 3 | Aceptada |
| HU05 | Editar e inactivar sede | 3 | Aceptada |
| HU06 | Crear usuario con rol y sede asignada | 5 | Aceptada |
| HU07 | Editar usuario | 3 | Aceptada |
| HU08 | Inactivar usuario | 2 | Aceptada |

## Evidencia de la demo

Recorrido ejecutado contra la API en funcionamiento:

1. Inicio de sesión del Administrador con credenciales válidas.
2. Intento con contraseña incorrecta: mensaje genérico que no revela el campo que falló.
3. Creación de la sede *Zona T*.
4. Creación del usuario `mesero1` con rol Mesero y sede *Zona T*.
5. Inicio de sesión del Mesero: accede con su rol y su sede asignada.
6. El Mesero intenta crear una sede: el sistema lo rechaza por rol insuficiente.
7. El Administrador inactiva la cuenta del Mesero.
8. El Mesero ya no puede autenticarse.
9. El token que el Mesero tenía en uso queda invalidado de inmediato.
10. El log de auditoría registra los once eventos de la sesión de demostración.

## Verificación de calidad

| Verificación | Resultado |
| ------------ | --------- |
| Pruebas automatizadas del backend | 92 pruebas, todas en verde |
| `manage.py check` | Sin incidencias |
| Build del frontend | Sin errores |
| Migraciones | Aplicadas sobre base de datos limpia |

## Decisiones tomadas durante el sprint

1. **Tiempo de inactividad: 3 minutos.** El documento de la HU02 y la propuesta comercial V1.1
   coinciden en 3 minutos; el backlog indicaba 15 minutos con aviso previo. Se resolvió a favor
   del documento de la historia, que es el más específico. **Pendiente de confirmación con el
   Product Owner** para actualizar el backlog.
2. **Bloqueo por intentos fallidos.** El backlog exige bloquear el acceso 5 minutos tras 3
   intentos fallidos consecutivos. La HU01 no lo contradice y es un control OWASP, por lo que se
   implementó.
3. **Invalidación de sesión en servidor.** Para cumplir el criterio "la sesión queda
   completamente invalidada en servidor (no solo frontend)" no bastaba con la expiración del
   token: cada petición autenticada verifica el estado de la sesión y aplica el corte por
   inactividad del lado del servidor.
4. **Sede obligatoria para Cajero y Mesero.** El alcance de estos roles se limita a su sede, por
   lo que una cuenta sin sede no podría operar. El Administrador puede quedar sin sede fija.
5. **Punto de extensión para la inactivación de sedes.** La HU05 exige impedir la inactivación de
   una sede con pedidos abiertos, pero el módulo de pedidos llega en el Sprint 3. Se dejó
   registrado el mecanismo `register_deactivation_guard`, ya cubierto por pruebas, para que las
   HU17 a HU21 lo implementen sin modificar el módulo de sedes.

## Retrospectiva — Start / Stop / Continue

**Start**
- Registrar en el acta de Sprint Planning las discrepancias detectadas entre el backlog y los
  documentos de las historias, para resolverlas con el Product Owner antes de desarrollar.

**Stop**
- Dejar criterios de aceptación que dependen de módulos de sprints posteriores sin un mecanismo
  explícito que los conecte. En este sprint se resolvió con un punto de extensión, pero la
  dependencia debió identificarse en la planificación.

**Continue**
- Una prueba automatizada por criterio de aceptación. Es lo que permitió cerrar las 8 historias
  con la Definition of Done cumplida y verificable.
- Una rama por historia y merge con `--no-ff`, que mantiene la trazabilidad historia → código.

## Preparación del Sprint 2

El Sprint 2 (07 — 20 sep) aborda el catálogo de productos, los proveedores y el inventario:
HU09 a HU16, 27 SP. Todas sus dependencias quedaron cubiertas: la entidad Sede existe, el
control de acceso por rol opera y el log de auditoría está disponible para todos los módulos.
