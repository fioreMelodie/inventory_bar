# Bar Inventory APP

Sistema de gestión integral de inventario y punto de venta para **Café Colombia Bar**
(sedes Galería, Zona T y Modelia).

Desarrollado por **DevSolutions S.A.S.** bajo metodología **Scrum**.

---

## Stack tecnológico

| Capa            | Tecnología                                   |
| --------------- | -------------------------------------------- |
| Backend         | Python 3.13 · Django 5.2 · Django REST Framework |
| Autenticación   | JWT (SimpleJWT) con blacklist en servidor    |
| Base de datos   | MySQL 8 (SQLite en desarrollo local)         |
| Frontend        | JavaScript · React 18 · Vite · Tailwind CSS  |
| Pruebas de API  | Postman                                      |
| Control de versiones | Git · GitHub                            |

> **Importante:** toda la interfaz de usuario está **en inglés** (requisito no funcional de la
> propuesta comercial). La documentación y los comentarios del código están en español.

---

## Estructura del repositorio

```
.
├── backend/              API REST en Django
│   ├── config/           Configuración del proyecto (settings, urls, wsgi)
│   ├── apps/             Aplicaciones del dominio
│   └── requirements.txt
├── frontend/             Aplicación React (UI en inglés)
│   └── src/
└── docs/                 Documentación del proyecto
    ├── historias de usuario/   Las 30 HU en PDF
    └── scrum/                  Evidencia Scrum por sprint
```

---

## Puesta en marcha

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env          # y ajustar credenciales
python manage.py migrate
python manage.py runserver
```

API disponible en `http://localhost:8000/api/`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Aplicación disponible en `http://localhost:5173`

---

## Flujo de trabajo Git

Según la *Guía de Scrum para el proyecto Café Colombia Bar*:

```
main
└── develop
    ├── feature/HU-01-login
    ├── feature/HU-02-cierre-sesion-inactividad
    └── ...
```

- Una rama `feature/HU-XX-descripcion` por historia de usuario.
- Commits con el identificador de la historia: `feat(HU-01): implementar autenticación`.
- Merge a `develop` con `--no-ff` para conservar la trazabilidad de cada historia.

---

## Roles del sistema

| Rol           | Alcance                                                          |
| ------------- | ---------------------------------------------------------------- |
| Administrador | Todas las sedes. Gestiona sedes, usuarios, mesas y productos.     |
| Cajero        | Su sede asignada. Cobros, facturación e inventario de su sede.    |
| Mesero        | Su sede asignada. Pedidos por mesa.                               |

No existe autoregistro: todas las cuentas las crea el Administrador.

Prueba de despliegue automatico.
