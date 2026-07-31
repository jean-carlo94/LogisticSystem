# LogisticSystem API

API REST multitenant con autenticación JWT, RBAC (roles/permisos), gestión de productos con imágenes y códigos de barras, estanterías de bodega con validación de capacidad, ventas, pedidos con state machine, y auditoría global. FastAPI + SQLAlchemy 2.0 async + PostgreSQL + Alembic.

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

**`Base`** (`app/core/database.py`) provee CRUD global: `get_id`, `get_all`, `create`, `update`, `delete`. Propaga property setters vía `setattr`. Soporta filtros genéricos con type coercion e `ILIKE`. Tenant scoping automático.

**`BaseRepository`** (`app/core/repository.py`) ABC con `model: type[Base]`. Repositorios heredan CRUD base + agregan queries específicas. Lee `current_tenant_id` del ContextVar automáticamente.

## Estructura

```
app/
├── main.py                   # FastAPI app, lifespan (seed), CORS, StaticFiles, exception handler
├── seed.json                 # Seed de permisos + roles (templates)
├── core/
│   ├── config.py             # pydantic-settings con @lru_cache (sin defaults hardcodeados)
│   ├── database.py           # async engine lazy + AsyncSession + Base (CRUD + filtros + tenant scoping)
│   ├── security.py           # JWT + bcrypt + get_current_user + require_permission + _tenant_context
│   ├── audit.py              # AuditLogger (serializa Pydantic/SQLAlchemy/dict, lee tenant context)
│   ├── pagination.py         # PaginatedResponse + PaginationParams + FilterParams
│   ├── storage.py            # StorageBackend ABC + LocalStorageBackend (S3 futuro)
│   ├── permissions.py        # PermissionCode enum (incluye TENANTS_MANAGE)
│   ├── exceptions.py         # AppException + NotFound/Conflict/Forbidden/Unauthorized/BadRequest/Validation
│   ├── repository.py         # BaseRepository ABC (lazy tenant_id del ContextVar)
│   ├── seed.py               # Permisos globales + admin default + seed_tenant_roles()
│   ├── tenant.py             # ContextVar current_tenant_id + resolve_tenant()
│   ├── email.py              # Envío de emails (Resend/SMTP)
│   ├── templates.py          # Templates Jinja2 para emails
│   └── rate_limit.py         # Rate limiter in-memory
├── api/
│   ├── dependencies.py       # get_audit_logger (dependencias compartidas)
│   └── v1/api.py             # Registro de routers
└── modules/
    ├── tenants/              # CRUD tenants + creación de roles/admin por tenant + settings (api_key, logo)
    ├── taxes/                # CRUD impuestos por tenant + asignación a productos (ProductTax)
    ├── customers/            # CRUD clientes por tenant + auto-detección en ventas/pedidos
    ├── products/             # CRUD + state machine (ProductState) + images + QR + barcode + dimensions + taxes
    ├── events/               # Audit log append-only (ActionType, tenant_id nullable)
    ├── users/                # Auth + profile + image + admin CRUD (tenant_id nullable)
    ├── roles/                # CRUD roles por tenant, permisos globales, asignaciones
    ├── shelves/              # CRUD estanterías + items + validación capacidad
    ├── categories/           # CRUD categorías por tenant + asignación a productos
    ├── sales/                # Crear ventas, descuento de stock producto + estantería
    └── orders/               # Pedidos con state machine (CREATED→PREPARING→READY→DELIVERED) + entrega crea venta
```

## Multitenant

Schema compartido (misma DB). Cada tenant es una empresa independiente. Aislamiento vía columna `tenant_id` + `ContextVar`.

| Concepto | Detalle |
|----------|---------|
| **Tablas con `tenant_id`** | users (nullable), products, categories, shelves, sales, orders, events (nullable), roles |
| **Sin `tenant_id`** | shelf_items, sale_items, order_items, product_categories, role_permissions, user_roles (scoped via FK padre), permissions (global) |
| **Unique constraints** | Compuestos `(tenant_id, campo)` para barcode, shelf code, category name, role name |
| **Platform admin** | `is_super_admin=True`, `tenant_id=NULL`. Sin `X-Tenant` header → ve todo. Con `X-Tenant: <slug>` → switchea a ese tenant |
| **Tenant user** | `tenant_id=X`. JWT incluye `tid`. Scoping automático, no necesita header |
| **Tenant context** | `current_tenant_id: ContextVar` → `BaseRepository` lo lee lazy → `Base.get_all/get_id` filtran WHERE |

### Crear tenant

`POST /tenants` (solo platform admin):
1. Crea registro en `tenants`
2. `seed_tenant_roles()` crea roles Admin/Operator/Viewer para ese tenant
3. Si se envían `admin_email` + `admin_password` → crea usuario admin con `tenant_id` y rol Admin

## Instalación

### Desarrollo

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

### Producción

```bash
cp .env.prod.example .env.prod
# Editar .env.prod con valores de producción
docker compose -f docker-compose.prod.yml up --build -d
```

**Diferencias con desarrollo:**

| Aspecto | Desarrollo | Producción |
|---------|-----------|------------|
| Source code | Volume mount `.` → `/app` | Imagen autocontenida |
| PostgreSQL | Puerto 5432 expuesto | Solo red interna |
| Uploads | Volume host `static/uploads` | Volumen Docker `uploads_data` |
| Rate limit | 1000 req/60s | 200 req/60s (configurable) |
| Body size | 10MB | 5MB (configurable) |
| CORS | `*` o `localhost:*` | Dominio explícito |
| Restart | `unless-stopped` | `always` |
| Healthcheck | Solo postgres | App + postgres |
| Recursos | Sin límites | CPU + memoria limitados |

Documentación: [Swagger](http://localhost:8000/docs) · [ReDoc](http://localhost:8000/redoc)

## Endpoints

### Auth

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| `POST` | `/api/v1/auth/register` | No | Registrar usuario |
| `POST` | `/api/v1/auth/login` | No | Login → JWT (24h, incluye `tid`) |
| `GET` | `/api/v1/auth/me` | Sí | Perfil completo (roles + permisos) |
| `PUT` | `/api/v1/auth/me` | Sí | Editar perfil propio |
| `POST` | `/api/v1/auth/me/image` | Sí | Subir avatar |
| `DELETE` | `/api/v1/auth/me/image` | Sí | Eliminar avatar |
| `POST` | `/api/v1/auth/forgot-password` | No | Solicitar reset password |
| `POST` | `/api/v1/auth/reset-password` | No | Resetear password con token |
| `POST` | `/api/v1/auth/activate` | No | Activar cuenta con token |
| `POST` | `/api/v1/auth/resend-activation` | No | Reenviar email de activación |

### Tenants

| Método | Ruta | Permiso | Descripción |
|--------|------|---------|-------------|
| `GET` | `/api/v1/tenants/` | `tenants_manage` | Listar tenants (paginado + filtros) |
| `POST` | `/api/v1/tenants/` | `tenants_manage` | Crear tenant + roles + admin opcional |
| `GET` | `/api/v1/tenants/{id}` | `tenants_manage` | Obtener tenant |
| `PUT` | `/api/v1/tenants/{id}` | `tenants_manage` | Actualizar tenant |
| `DELETE` | `/api/v1/tenants/{id}` | `tenants_manage` | Desactivar tenant (soft delete) |

### Productos

| Método | Ruta | Permiso | Descripción |
|--------|------|---------|-------------|
| `GET` | `/api/v1/products/` | `products_read` | Listar (paginado + filtros) |
| `GET` | `/api/v1/products/{id}` | `products_read` | Obtener |
| `POST` | `/api/v1/products/` | `products_create` | Crear |
| `PUT` | `/api/v1/products/{id}` | `products_update` | Actualizar |
| `DELETE` | `/api/v1/products/{id}` | `products_delete` | Eliminar |
| `POST` | `/api/v1/products/{id}/image` | `products_update` | Subir imagen |
| `DELETE` | `/api/v1/products/{id}/image` | `products_update` | Eliminar imagen |
| `GET` | `/api/v1/products/{id}/qr` | `products_read` | Datos QR (JSON) |

### Categorías

| Método | Ruta | Permiso | Descripción |
|--------|------|---------|-------------|
| `GET` | `/api/v1/categories/` | `categories_read` | Listar (paginado + filtros) |
| `POST` | `/api/v1/categories/` | `categories_create` | Crear |
| `PUT` | `/api/v1/categories/{id}` | `categories_update` | Actualizar |
| `DELETE` | `/api/v1/categories/{id}` | `categories_delete` | Eliminar |

### Estanterías

| Método | Ruta | Permiso | Descripción |
|--------|------|---------|-------------|
| `GET` | `/api/v1/shelves/` | `shelves_read` | Listar (paginado + filtros) |
| `GET` | `/api/v1/shelves/{id}` | `shelves_read` | Detalle + items + peso/volumen actual |
| `POST` | `/api/v1/shelves/` | `shelves_create` | Crear |
| `PUT` | `/api/v1/shelves/{id}` | `shelves_update` | Actualizar |
| `DELETE` | `/api/v1/shelves/{id}` | `shelves_delete` | Eliminar (debe estar vacía) |
| `POST` | `/api/v1/shelves/{id}/items` | `shelves_update` | Asignar producto (upsert) |
| `PUT` | `/api/v1/shelves/{id}/items/{item_id}` | `shelves_update` | Cambiar cantidad |
| `DELETE` | `/api/v1/shelves/{id}/items/{item_id}` | `shelves_update` | Desasignar producto |

### Ventas

| Método | Ruta | Permiso | Descripción |
|--------|------|---------|-------------|
| `GET` | `/api/v1/sales/` | `sales_read` | Listar (paginado + filtros) |
| `GET` | `/api/v1/sales/{id}` | `sales_read` | Detalle + items |
| `POST` | `/api/v1/sales/` | `sales_create` | Crear venta (descuenta stock) |

### Pedidos

| Método | Ruta | Permiso | Descripción |
|--------|------|---------|-------------|
| `GET` | `/api/v1/orders/` | `orders_read` | Listar (paginado + filtros) |
| `GET` | `/api/v1/orders/{id}` | `orders_read` | Detalle + items |
| `POST` | `/api/v1/orders/` | `orders_create` | Crear pedido (valida stock) |
| `POST` | `/api/v1/orders/{id}/prepare` | `orders_manage` | CREATED → PREPARING |
| `POST` | `/api/v1/orders/{id}/ready` | `orders_manage` | PREPARING → READY |
| `POST` | `/api/v1/orders/{id}/deliver` | `orders_manage` | READY → DELIVERED (crea venta) |

### Eventos (auditoría)

| Método | Ruta | Permiso | Descripción |
|--------|------|---------|-------------|
| `GET` | `/api/v1/events/` | `events_read` | Listar (paginado + filtros) |
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
| `POST` | `/api/v1/users/{id}/image` | `users_manage` | Subir imagen |
| `DELETE` | `/api/v1/users/{id}/image` | `users_manage` | Eliminar imagen |
| `GET` | `/api/v1/users/{id}/roles` | `users_manage` | Ver roles |
| `POST` | `/api/v1/users/{id}/roles` | `users_manage` | Asignar rol |

## Filtros genéricos

Todas las rutas `GET /list` aceptan filtros como query params. El sistema convierte automáticamente el valor al tipo de la columna. `tenant_id` se excluye automáticamente (gestionado por el sistema multitenant).

| Tipo de columna | Comportamiento | Ejemplo |
|-----------------|---------------|---------|
| `String` / `Text` | `ILIKE %valor%` (case-insensitive, parcial) | `?name=tornillo` → "Tornillo M3" |
| `Integer` | `==` exacto | `?stock=100` |
| `Float` | `==` exacto | `?price=15.0` |
| `Boolean` | `==` exacto | `?is_active=true` |
| `Enum` | `==` exacto | `?state=ACTIVE` |
| `DateTime` | Range día exacto `>= date AND < date+1d` | `?created_at=2026-07-31` |

Múltiples filtros se combinan con `AND`. Ejemplos:

```
GET /products/?state=ACTIVE&price=15.0
GET /users/?is_active=true&first_name=admin
GET /shelves/?aisle=A&row=1
GET /events/?action=CREATE&entity_type=Product
GET /tenants/?is_active=true&name=acme
GET /orders/?status=CREATED&customer_name=juan
GET /orders/?status=DELIVERED&created_at=2026-07-31
GET /sales/?created_at=2026-07-31
```

Campos bloqueados: `hashed_password` en users (ignorado por seguridad), `tenant_id` en todas las entidades.

## RBAC — Roles y Permisos

**Tablas:** `permissions` (global), `roles` (por tenant), `role_permissions` (n-m), `user_roles` (n-m).

**Permisos** definidos en `app/core/permissions.py` (`PermissionCode` enum):
`products_create`, `products_read`, `products_update`, `products_delete`, `events_read`, `roles_manage`, `users_manage`, `shelves_create`, `shelves_read`, `shelves_update`, `shelves_delete`, `categories_create`, `categories_read`, `categories_update`, `categories_delete`, `sales_create`, `sales_read`, `orders_create`, `orders_read`, `orders_manage`, `tenants_manage`

**Seed** (`app/seed.json`):
- Permisos globales (idempotente, se crean al primer arranque)
- Roles (Admin/Operator/Viewer) se crean por tenant al llamar `POST /tenants`
- Platform admin default: `ADMIN_EMAIL`/`ADMIN_PASSWORD` env vars, `is_super_admin=True`, sin `tenant_id`

| Rol | Permisos |
|-----|----------|
| `Admin` | todos excepto `tenants_manage` |
| `Operator` | products_create/read/update, shelves_read/update, categories_read, sales_create/read, orders_create/read/manage |
| `Viewer` | products_read, shelves_read, categories_read, sales_read, orders_read, events_read |

**`require_permission(code)`** (`app/core/security.py`):
- `is_super_admin=True` → bypass total
- Query: User → UserRole → Role → RolePermission → Permission
- Sin permiso → 403

**`tenants_manage`**: solo platform admin (`is_super_admin=True`). Roles por tenant NO incluyen este permiso.

## Auditoría global

`AuditLogger` (`app/core/audit.py`) inyectable vía `Depends(get_audit_logger)`. Serializa Pydantic schemas, SQLAlchemy entities, dicts. Filtra `hashed_password`. Lee `current_tenant_id` del ContextVar para eventos.

```python
await self.audit.log_create("Product", product.id, user_id, product)
await self.audit.log_update("Product", product.id, user_id, product_in)
await self.audit.log_status_change("Product", id, user_id, old, new)
await self.audit.log_delete("Product", product.id, user_id, product)
```

## Seguridad

### Autenticación
- **bcrypt** para hashing de contraseñas con salt automático
- **JWT HS256** con `SECRET_KEY` (mín. 32 caracteres). Incluye `sub`, `exp`, `ver`, `tid`
- **Token version** — al cambiar contraseña se invalida la sesión de todos los dispositivos
- **Rate limit** por IP: 1000 req/60s global, 5 req/60s forgot-password, 10 req/60s activate

### Protección de datos
- `hashed_password` excluido de filtros y audit log
- Tokens de reset/activación hasheados con SHA-256 en BD
- **Mitigación de timing attack** en forgot-password con delay aleatorio
- **Límite de body size**: `REQUEST_BODY_MAX_SIZE_MB` (default 10), retorna 413

### Upload de archivos
- Validación MIME: JPEG, PNG, WebP, GIF, SVG
- Nombres UUID (previene path traversal), límite 10MB

### Headers de seguridad
`X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, `Referrer-Policy`, `Cache-Control`

### Multitenant
- Aislamiento automático vía `ContextVar` + `BaseRepository`
- `X-Tenant` header para platform admin switcheo de contexto
- JWT incluye `tid` para usuarios con tenant
- `current_tenant_id` se lee lazy en cada método (no en `__init__` del repo)
- `tenant_id` se excluye de filtros de query params

## Almacenamiento de imágenes

`app/core/storage.py` — adapter pattern:
- `LocalStorageBackend` — guarda en `static/uploads/{entity}/{prefix}_{uuid}.{ext}`
- `S3StorageBackend` — futuro, configurable vía `STORAGE_BACKEND=s3`
- Imágenes servidas vía `StaticFiles` en `/static`
- `image_url` computado en response JSON

## Validación de capacidad (estanterías)

Al asignar producto a estantería se validan: dimensiones, peso, volumen y stock disponible. Error → 400 con detalle concatenado.

**POST /items upsert**: si el producto ya existe, suma cantidad (no 409).

## Modelos

### User

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | int | PK |
| `tenant_id` | int\|null | FK tenants, null = platform admin |
| `email` | str(255) | único global, indexado |
| `hashed_password` | str(255) | bcrypt |
| `first_name` | str\|null | |
| `last_name` | str\|null | |
| `phone` | str\|null | |
| `city` | str\|null | |
| `country` | str\|null | |
| `is_active` | bool | default true |
| `is_super_admin` | bool | bypass permisos |
| `token_version` | int | invalidación de sesiones |
| `image_path` | str(500)\|null | |
| `created_at` | datetime | |
| `updated_at` | datetime | |

### Product

| Campo | Tipo | Setter |
|-------|------|--------|
| `id` | int | — |
| `tenant_id` | int | FK tenants, NOT NULL |
| `name` | str(200) | `.strip()` |
| `description` | str\|null | — |
| `price` | float | `round(2)` |
| `stock` | int | `max(0)` |
| `state` | enum | ACTIVE\|INACTIVE\|NO_STOCK\|DISCONTINUED |
| `barcode` | str(128)\|null | unique `(tenant_id, barcode)`, indexado |
| `image_path` | str(500)\|null | |
| `weight_kg` | float | `max(0)` |
| `width_cm` | float | `max(0)` |
| `height_cm` | float | `max(0)` |
| `depth_cm` | float | `max(0)` |
| `create_at` | datetime | |
| `update_at` | datetime | |

State machine: stock=0 → NO_STOCK, stock>0 + NO_STOCK → ACTIVE.

### Category

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | int | PK |
| `tenant_id` | int | FK tenants, unique `(tenant_id, name)` |
| `name` | str(100) | |
| `description` | str\|null | |

### Shelf

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | int | PK |
| `tenant_id` | int | FK tenants, unique `(tenant_id, code)` |
| `name` | str(100) | |
| `code` | str(50) | código único por tenant |
| `aisle` | str(20) | pasillo |
| `row` | int | fila |
| `level` | int | nivel |
| `max_weight_kg` | float | 0=sin límite |
| `width_cm` | float | 0=sin límite |
| `height_cm` | float | 0=sin límite |
| `depth_cm` | float | 0=sin límite |

### Sale

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | int | PK |
| `tenant_id` | int | FK tenants |
| `customer_name` | str(200) | |
| `total` | float | |
| `status` | enum | COMPLETED\|CANCELLED |
| `notes` | str\|null | |
| `created_by` | int | FK users |

### Order

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | int | PK |
| `tenant_id` | int | FK tenants |
| `customer_name` | str(200) | |
| `total` | float | |
| `status` | enum | CREATED→PREPARING→READY→DELIVERED |
| `notes` | str\|null | |
| `created_by` | int | FK users |

### Event

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | int | PK |
| `tenant_id` | int\|null | nullable (platform-level events) |
| `entity_type` | str(100) | |
| `entity_id` | int | |
| `action` | enum | CREATE\|UPDATE\|DELETE\|STATUS_CHANGED |
| `user_id` | int | FK users |
| `description` | str\|null | JSON |
| `create_at` | datetime | |

### Tenant

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | int | PK |
| `name` | str(200) | nombre empresa |
| `slug` | str(100) | único, URL-safe (regex `^[a-z0-9-]+$`) |
| `is_active` | bool | default true |

## Variables de entorno

| Variable | Default | Descripción |
|----------|---------|-------------|
| `DATABASE_URL` | *(requerido)* | postgresql://user:pass@host:5432/db |
| `SECRET_KEY` | *(requerido)* | JWT signing key (mín. 32 caracteres) |
| `ADMIN_EMAIL` | *(vacío)* | Email del admin creado en primer arranque |
| `ADMIN_PASSWORD` | *(vacío)* | Password del admin |
| `ACCESS_TOKEN_EXPIRE_HOURS` | *(requerido)* | Expiración JWT |
| `API_V1_STR` | *(requerido)* | Prefijo API |
| `PROJECT_NAME` | *(requerido)* | Título docs |
| `CORS_ORIGINS` | *(requerido)* | JSON array, ej: `["http://localhost:5173"]` |
| `RATE_LIMIT_REQUESTS` | *(requerido)* | Requests por ventana |
| `RATE_LIMIT_WINDOW` | *(requerido)* | Ventana en segundos |
| `REQUEST_BODY_MAX_SIZE_MB` | *(requerido)* | Límite body size |
| `STORAGE_PATH` | *(requerido)* | Directorio uploads |
| `RESEND_API_KEY` | *(vacío)* | API key Resend |
| `RESEND_FROM_EMAIL` | *(requerido)* | Remitente emails |
| `PASSWORD_RESET_TOKEN_EXPIRE_MINUTES` | *(requerido)* | Expiración token reset |
| `ACCOUNT_ACTIVATION_EXPIRE_HOURS` | *(requerido)* | Expiración activación |
| `FRONTEND_URL` | *(requerido)* | URL frontend para links de email |

Sin defaults hardcodeados. Solo `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `RESEND_API_KEY` tienen default vacío (opcionales reales).

## Transacciones y Migraciones

- **Transacciones:** `get_db` commit al final del request, rollback en excepción
- **Migraciones:** `alembic upgrade head` en `start.sh`. Generar: `python -m alembic revision --autogenerate -m "desc"`

## Seed

`app/seed.json` define permisos y roles template. `app/core/seed.py` carga permisos globales al primer arranque. `seed_tenant_roles(tenant_id)` crea roles para un tenant específico al llamar `POST /tenants`. Platform admin se crea con `ADMIN_EMAIL`/`ADMIN_PASSWORD`.

## Agregar nuevo módulo

```
app/modules/nuevo/
├── __init__.py
├── model.py          # class Nuevo(Base): ...
├── schema.py         # Pydantic DTOs
├── repository.py     # class NuevoRepo(BaseRepository): model = Nuevo
├── service.py        # class NuevoService: __init__(repo, audit?)
├── router.py         # Endpoints
└── deps.py           # get_nuevo_service(db=Depends(get_db))
```

Registrar router en `app/api/v1/api.py`. Importar modelo en `alembic/env.py`. Si el módulo es tenant-scoped, agregar `tenant_id` FK al modelo y heredar de `BaseRepository` (el scoping es automático).
