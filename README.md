# LogisticSystem API

API REST con autenticación JWT, RBAC (roles/permisos), gestión de productos y auditoría global. FastAPI + SQLAlchemy 2.0 async + PostgreSQL + Alembic.

## Arquitectura

```
Router (async) → Depends → Service (async) → Repository → Base (async CRUD)
```

| Capa | Ubicación | Responsabilidad |
|------|-----------|-----------------|
| Router | `modules/{name}/router.py` | Endpoints HTTP, validación I/O |
| Service | `modules/{name}/service.py` | Lógica de negocio |
| Repository | `modules/{name}/repository.py` | Acceso a datos (hereda de `BaseRepository`) |
| Model | `modules/{name}/model.py` | ORM + queries de clase (hereda de `Base`) |
| Schema | `modules/{name}/schema.py` | Pydantic DTOs |

**`Base`** (`app/core/database.py`) provee CRUD global: `get_id`, `get_all`, `create`, `save`, `update`, `delete`. Propaga property setters vía `setattr`.

**`BaseRepository`** (`app/core/repository.py`) ABC con `model: type[Base]`. Repositorios heredan CRUD base + agregan queries específicas.

## Estructura

```
app/
├── main.py                   # FastAPI app, lifespan (seed), CORS, exception handler
├── seed.json                 # Seed inicial de permisos y roles
├── core/
│   ├── config.py             # pydantic-settings con @lru_cache
│   ├── database.py           # async engine + AsyncSession + Base (CRUD global)
│   ├── security.py           # JWT + bcrypt + get_current_user + require_permission
│   ├── audit.py              # AuditLogger inyectable (Pydantic/SQLAlchemy/dict)
│   ├── pagination.py         # PaginatedResult + PaginatedResponse + PaginationParams
│   ├── permissions.py        # PermissionCode enum (constantes de permisos)
│   ├── exceptions.py         # AppException + NotFound/Conflict/Forbidden/Unauthorized
│   ├── repository.py         # BaseRepository ABC
│   └── seed.py               # Carga seed.json → DB (primer arranque)
├── api/
│   ├── dependencies.py       # get_audit_logger (dependencias compartidas)
│   └── v1/api.py             # Registro de routers
└── modules/
    ├── products/             # CRUD productos + máquina de estados
    ├── events/               # Auditoría genérica (solo lectura)
    ├── users/                # Auth + perfil + admin CRUD usuarios
    └── roles/                # CRUD roles, permisos, asignaciones
```

## Instalación

```bash
git clone <repo-url> && cd LogisticSystemAPI
cp .env.example .env
# Editar .env: DATABASE_URL, SECRET_KEY

docker compose up --build -d
curl http://localhost:8000/health  # {"status":"healthy"}
```

**Desarrollo local:**
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
# Configurar .env con DATABASE_URL y SECRET_KEY
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Documentación: [Swagger](http://localhost:8000/docs) · [ReDoc](http://localhost:8000/redoc)

## Endpoints

### Auth

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| `POST` | `/api/v1/auth/register` | No | Registrar usuario |
| `POST` | `/api/v1/auth/login` | No | Login → JWT (24h) |
| `GET` | `/api/v1/auth/me` | Sí | Perfil completo (roles + permisos) |
| `PUT` | `/api/v1/auth/me` | Sí | Editar perfil propio |

### Productos

| Método | Ruta | Permiso | Descripción |
|--------|------|---------|-------------|
| `GET` | `/api/v1/products/` | `products_read` | Listar (paginado) |
| `GET` | `/api/v1/products/{id}` | `products_read` | Obtener |
| `POST` | `/api/v1/products/` | `products_create` | Crear |
| `PUT` | `/api/v1/products/{id}` | `products_update` | Actualizar |
| `DELETE` | `/api/v1/products/{id}` | `products_delete` | Eliminar |

### Eventos (auditoría)

| Método | Ruta | Permiso | Descripción |
|--------|------|---------|-------------|
| `GET` | `/api/v1/events/` | `events_read` | Listar (paginado) |
| `GET` | `/api/v1/events/{id}` | `events_read` | Obtener |
| `GET` | `/api/v1/{entity_type}/{entity_id}/events/` | `events_read` | Eventos de entidad |

### Roles

| Método | Ruta | Permiso | Descripción |
|--------|------|---------|-------------|
| `GET` | `/api/v1/roles/` | auth | Listar roles |
| `POST` | `/api/v1/roles/` | `roles_manage` | Crear rol |
| `PUT` | `/api/v1/roles/{id}` | `roles_manage` | Editar rol |
| `DELETE` | `/api/v1/roles/{id}` | `roles_manage` | Eliminar rol |
| `GET` | `/api/v1/roles/permissions/` | `roles_manage` | Listar permisos disponibles |
| `GET` | `/api/v1/roles/{id}/permissions` | auth | Ver permisos de un rol |
| `POST` | `/api/v1/roles/{id}/permissions` | `roles_manage` | Asignar permisos a rol |
| `POST` | `/api/v1/roles/assign` | `users_manage` | Asignar rol a usuario |

### Usuarios (admin)

| Método | Ruta | Permiso | Descripción |
|--------|------|---------|-------------|
| `GET` | `/api/v1/users/` | `users_manage` | Listar usuarios |
| `GET` | `/api/v1/users/{id}` | `users_manage` | Obtener usuario |
| `PUT` | `/api/v1/users/{id}` | `users_manage` | Editar usuario |
| `DELETE` | `/api/v1/users/{id}` | `users_manage` | Eliminar usuario |

## RBAC — Roles y Permisos

**Tablas:** `permissions`, `roles`, `role_permissions` (n-m), `user_roles` (n-m, usuario con N roles).

**Códigos** definidos en `app/core/permissions.py` (`PermissionCode` enum):
`products_create`, `products_read`, `products_update`, `products_delete`, `events_read`, `roles_manage`, `users_manage`

**Seed inicial** (`app/seed.json` → `app/core/seed.py`):

| Rol | Permisos |
|-----|----------|
| `Admin` | todos |
| `Operator` | products_create, products_read, products_update |
| `Viewer` | products_read |

**`require_permission(code)`** (`app/core/security.py`) — dependencia inyectable:
- `is_super_admin=True` → bypass total
- Query: User → UserRole → RolePermission → Permission
- Sin permiso → 403

**Uso en rutas:**
```python
@router.post("/")
async def create(
    ...,
    _perm = Depends(require_permission(PermissionCode.PRODUCTS_CREATE)),
): ...
```

## Auditoría global

`AuditLogger` (`app/core/audit.py`) inyectable vía `Depends(get_audit_logger)`. Serializa automáticamente Pydantic schemas, SQLAlchemy entities (vía `class_mapper`) y dicts. Filtra `hashed_password`.

```python
await self.audit.log_create("Product", product.id, user_id, product)
await self.audit.log_update("Product", product.id, user_id, product_in)
await self.audit.log_status_change("Product", id, user_id, old, new)
await self.audit.log_delete("Product", product.id, user_id, product)
```

## Modelos

### User

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | int | PK |
| `email` | str(255) | único, indexado |
| `hashed_password` | str(255) | bcrypt |
| `first_name` | str\|null | |
| `last_name` | str\|null | |
| `phone` | str\|null | |
| `city` | str\|null | |
| `country` | str\|null | |
| `is_active` | bool | default true |
| `is_super_admin` | bool | bypass permisos, default false |
| `created_at` | datetime | server_default now() |
| `updated_at` | datetime | onupdate now() |

### Product

| Campo | Tipo | Setter |
|-------|------|--------|
| `id` | int | — |
| `name` | str(200) | `.strip()` |
| `description` | str\|null | — |
| `price` | float | `round(2)`, gt=0 |
| `stock` | int | `max(0)`, ge=0 |
| `state` | enum | ACTIVE\|INACTIVE\|NO_STOCK\|DISCONTINUED |
| `create_at` | datetime | server_default now() |
| `update_at` | datetime | onupdate now() |

Máquina de estados: stock=0 → NO_STOCK, stock>0 + NO_STOCK → ACTIVE.

### Event

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | int | PK |
| `entity_type` | str(100) | "Product", "User", ... |
| `entity_id` | int | |
| `action` | enum | CREATE\|UPDATE\|DELETE\|STATUS_CHANGED |
| `user_id` | int | FK users, indexado |
| `description` | str\|null | JSON |
| `create_at` | datetime | server_default now() |

Índice compuesto: `(entity_type, entity_id)`.

### Role

| Campo | Tipo |
|-------|------|
| `id` | int PK |
| `name` | str(100) único |
| `description` | str\|null |
| `created_at` | datetime |
| `updated_at` | datetime |

### Permission

| Campo | Tipo |
|-------|------|
| `id` | int PK |
| `code` | str(100) único |
| `description` | str\|null |

## Variables de entorno

| Variable | Default | Descripción |
|----------|---------|-------------|
| `DATABASE_URL` | *(requerido)* | postgresql://user:pass@host:5432/db |
| `SECRET_KEY` | *(requerido)* | JWT signing key |
| `API_V1_STR` | `/api/v1` | Prefijo API |
| `PROJECT_NAME` | `LogisticSystem` | Título docs |
| `ACCESS_TOKEN_EXPIRE_HOURS` | `24` | Expiración JWT |
| `CORS_ORIGINS` | `["*"]` | Orígenes CORS |
| `APP_PORT` | `8000` | Puerto HTTP |

## Transacciones y Migraciones

- **Transacciones:** `get_db` hace commit al final del request, rollback en excepción. `Base` usa `flush` (no `commit`).
- **Migraciones:** Alembic ejecutado en `start.sh` al iniciar (`alembic upgrade head`). Generar nuevas: `python -m alembic revision --autogenerate -m "descripción"`.

## Seed

`app/seed.json` define permisos y roles iniciales. `app/core/seed.py` lo carga al primer arranque (si tabla permissions vacía). Para agregar permisos/roles: editar el JSON + `app/core/permissions.py`.

## Agregar nuevo módulo

```
app/modules/nuevo/
├── __init__.py       # from .router import router
├── enums.py          # (opcional)
├── model.py          # class Nuevo(Base): ...
├── schema.py         # Pydantic DTOs
├── repository.py     # class NuevoRepo(BaseRepository): model = Nuevo
├── service.py        # class NuevoService: __init__(repo, audit?)
├── router.py         # Endpoints
└── deps.py           # get_nuevo_service(db=Depends(get_db))
```

Registrar router en `app/api/v1/api.py`. Importar modelo en `alembic/env.py`. Para auditoría: `audit: AuditLogger = Depends(get_audit_logger)`.
