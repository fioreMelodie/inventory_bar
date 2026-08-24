# Definition of Done — Bar Inventory APP

Acuerdo del equipo sobre cuándo una Historia de Usuario se considera **terminada**.
Tomado de la *Guía de Scrum para el proyecto Café Colombia Bar*, sección 11.

Una historia está DONE cuando cumple **todas** estas condiciones:

| # | Condición | Verificación |
| - | --------- | ------------ |
| 1 | Desarrollo completado | Backend y frontend implementados |
| 2 | Criterios de aceptación cumplidos | Contrastados uno a uno contra el documento de la HU |
| 3 | Código versionado en Git | Rama `feature/HU-XX-*` mergeada a `develop` |
| 4 | Code Review realizado | Revisión por otro integrante del equipo |
| 5 | Pruebas ejecutadas | Pruebas automatizadas del backend en verde |
| 6 | Sin errores críticos conocidos | `manage.py check` y build del frontend sin errores |
| 7 | Integración realizada | Frontend consume la API real, sin datos simulados |
| 8 | Validación del Product Owner | Demo en la Sprint Review |

## Criterios transversales obligatorios

Aplican a toda historia, sin excepción:

- **Interfaz en inglés.** Todo texto visible al usuario final está en inglés (requisito no
  funcional de la propuesta comercial V1.1).
- **Responsive.** La vista es operable desde Chrome en escritorio, tablet y móvil.
- **Auditoría.** Toda acción relevante genera un registro inmutable en el log de eventos con
  usuario, tipo de evento, entidad afectada, sede, fecha y hora.
- **Alcance por sede.** El Administrador ve todas las sedes; Cajero y Mesero solo la suya.
- **Seguridad OWASP Top 10.** Contraseñas cifradas, control de acceso verificado en servidor,
  sin exposición de información sensible en los mensajes de error.
- **Rendimiento.** La transacción responde en menos de 2 segundos en condiciones normales.
