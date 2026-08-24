# Sprint 1 — Autenticación, Sedes y Usuarios

| Campo | Valor |
| ----- | ----- |
| Fechas | 24 de agosto — 06 de septiembre de 2026 |
| Duración | 2 semanas |
| Story Points | 27 SP |
| Historias | HU01 · HU02 · HU03 · HU04 · HU05 · HU06 · HU07 · HU08 |

## Sprint Goal

Establecer la base completa del sistema: autenticación segura, control de sesiones, la entidad
Sede como unidad organizativa, y el control de acceso basado en roles (Administrador, Cajero,
Mesero) con la asignación de usuarios a sus sedes correspondientes.

## Sprint Backlog

| ID | Historia de Usuario | Módulo | Prioridad | SP | Rama |
| -- | ------------------- | ------ | --------- | -- | ---- |
| HU01 | Inicio de sesión con credenciales | Autenticación | Alta | 5 | `feature/HU-01-login` |
| HU02 | Cierre automático de sesión por inactividad | Autenticación | Alta | 3 | `feature/HU-02-cierre-sesion-inactividad` |
| HU03 | Cierre de sesión manual y pérdida de conexión | Autenticación | Alta | 3 | `feature/HU-03-cierre-sesion-manual` |
| HU04 | Crear sede | Administración de Sedes | Alta | 3 | `feature/HU-04-crear-sede` |
| HU05 | Editar e inactivar sede | Administración de Sedes | Alta | 3 | `feature/HU-05-editar-inactivar-sede` |
| HU06 | Crear usuario con rol y sede asignada | Gestión de Usuarios | Alta | 5 | `feature/HU-06-crear-usuario` |
| HU07 | Editar usuario | Gestión de Usuarios | Alta | 3 | `feature/HU-07-editar-usuario` |
| HU08 | Inactivar usuario | Gestión de Usuarios | Alta | 2 | `feature/HU-08-inactivar-usuario` |

## Entregables semanales

- **Semana 1 (24 — 30 ago):** HU01 · HU02 · HU03 · HU04 · HU05 — 17 SP
- **Semana 2 (31 ago — 06 sep):** HU06 · HU07 · HU08 — 10 SP

## Decisiones técnicas del sprint

1. **Stack.** Backend Python/Django + Django REST Framework; frontend JavaScript/React con Vite
   y Tailwind; base de datos MySQL 8 (SQLite en desarrollo local).
2. **Sesión con JWT.** Se usa SimpleJWT con *blacklist* para poder invalidar la sesión **en
   servidor**, tal como exige el criterio de aceptación de la HU02. El `access token` dura
   3 minutos, alineado con el tiempo de inactividad.
3. **Modelo de usuario propio.** Se extiende `AbstractBaseUser` para incorporar `rol`, `sede` y
   el campo `activo`, en lugar de usar el modelo por defecto de Django.
4. **Tiempo de inactividad: 3 minutos.** El documento de la HU02 y la propuesta comercial V1.1
   coinciden en 3 minutos. El backlog menciona 15 minutos con aviso previo; se resuelve la
   discrepancia a favor del documento de la historia, que es el más específico.
5. **Bloqueo por intentos fallidos.** El backlog exige bloquear el acceso 5 minutos tras 3
   intentos fallidos consecutivos. La HU01 no lo contradice y es un control OWASP, por lo que
   se implementa.

## Dependencias

Ninguna historia del Sprint 1 depende de sprints anteriores. Dentro del sprint:
HU06 requiere HU04 (la sede debe existir para poder asignarla a un usuario).
