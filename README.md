# LogisticSystem API

API REST con autenticación JWT, RBAC (roles/permisos), gestión de productos con imágenes y códigos de barras, estanterías de bodega con validación de capacidad, y auditoría global. FastAPI + SQLAlchemy 2.0 async + PostgreSQL + Alembic.

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

**`Base`** (`app/core/database.py`) provee CRUD global: `get_id`, `get_all`, `create`, `save`, `update`, `delete`. Propaga property setters vía `setattr`. Soporta filtros genéricos con type coercion e `ILIKE` para strings.

**`BaseRepository`** (`app/core/repository.py`) ABC con `model: type[Base]`. Repositorios heredan CRUD base + agregan queries específicas.

## Estructura

```
app/
├── main.py                   # FastAPI app, lifespan (seed), CORS, StaticFiles, exception handler
├── seed.json                 # Seed inicial de permisos, roles y admin default
├── core/
│   ├── config.py             # pydantic-settings con @lru_cache
│   ├── database.py           # async engine + AsyncSession + Base (CRUD + filtros)
│   ├── security.py           # JWT + bcrypt + get_current_user + require_permission
│   ├── audit.py              # AuditLogger inyectable (Pydantic/SQLAlchemy/dict)
│   ├── pagination.py         # PaginatedResult + PaginatedResponse + PaginationParams + FilterParams
│   ├── storage.py            # StorageBackend ABC + LocalStorageBackend (S3 futuro)
│   ├── permissions.py        # PermissionCode enum (constantes de permisos)
│   ├── exceptions.py         # AppException + NotFound/Conflict/Forbidden/Unauthorized/Validation
│   ├── repository.py         # BaseRepository ABC
│   └── seed.py               # Carga seed.json → DB + admin default (primer arranque)
├── api/
│   ├── dependencies.py       # get_audit_logger (dependencias compartidas)
│   └── v1/api.py             # Registro de routers
└── modules/
    ├── products/             # CRUD + state machine + imágenes + QR + barcode + dimensiones
    ├── shelves/              # CRUD estanterías + asignación productos + validación capacidad
    ├── events/               # Auditoría genérica (solo lectura)
    ├── users/                # Auth + perfil + imagen + admin CRUD usuarios
    └── roles/                # CRUD roles, permisos, asignaciones
```

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
# Editar .env.prod con valores de producción:
#   SECRET_KEY (generar con: openssl rand -base64 48)
#   POSTGRES_PASSWORD (contraseña segura)
#   ADMIN_EMAIL / ADMIN_PASSWORD (admin inicial)
#   CORS_ORIGINS (dominio del frontend en producción)
#   FRONTEND_URL (URL del frontend para links de email)

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

Para producción con reverse proxy (nginx/traefik), apuntar al puerto 8000 del contenedor y configurar TLS en el proxy. La app acepta `--proxy-headers` para respetar `X-Forwarded-*`.

Documentación: [Swagger](http://localhost:8000/docs) · [ReDoc](http://localhost:8000/redoc)

**Admin default:** Solo se crea si se configuran `ADMIN_EMAIL` y `ADMIN_PASSWORD` en `.env`. Si no se definen, no se crea ningún admin por defecto.

**CORS:** Configurar `CORS_ORIGINS` con los orígenes del frontend. Si se deja vacío, se permite cualquier origen (`*`) pero sin credenciales. Para solicitudes con cookies o `Authorization`, especificar orígenes explícitos:

```bash
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]
```

## Endpoints

### Auth

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| `POST` | `/api/v1/auth/register` | No | Registrar usuario |
| `POST` | `/api/v1/auth/login` | No | Login → JWT (24h) |
| `GET` | `/api/v1/auth/me` | Sí | Perfil completo (roles + permisos) |
| `PUT` | `/api/v1/auth/me` | Sí | Editar perfil propio |
| `POST` | `/api/v1/auth/me/image` | Sí | Subir avatar |
| `DELETE` | `/api/v1/auth/me/image` | Sí | Eliminar avatar |

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

### Estanterías

| Método | Ruta | Permiso | Descripción |
|--------|------|---------|-------------|
| `GET` | `/api/v1/shelves/` | `shelves_read` | Listar (paginado + filtros) |
| `GET` | `/api/v1/shelves/{id}` | `shelves_read` | Detalle + items + peso actual |
| `POST` | `/api/v1/shelves/` | `shelves_create` | Crear |
| `PUT` | `/api/v1/shelves/{id}` | `shelves_update` | Actualizar |
| `DELETE` | `/api/v1/shelves/{id}` | `shelves_delete` | Eliminar (debe estar vacía) |
| `POST` | `/api/v1/shelves/{id}/items` | `shelves_update` | Asignar producto |
| `PUT` | `/api/v1/shelves/{id}/items/{item_id}` | `shelves_update` | Cambiar cantidad |
| `DELETE` | `/api/v1/shelves/{id}/items/{item_id}` | `shelves_update` | Desasignar producto |

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

Todas las rutas `GET /list` aceptan filtros como query params. El sistema convierte automáticamente el valor al tipo de la columna.

| Tipo de columna | Comportamiento | Ejemplo |
|-----------------|---------------|---------|
| `String` / `Text` | `ILIKE %valor%` (case-insensitive, parcial) | `?name=tornillo` → "Tornillo M3" |
| `Integer` | `==` exacto | `?stock=100` |
| `Float` | `==` exacto | `?price=15.0` |
| `Boolean` | `==` exacto | `?is_active=true` |
| `Enum` | `==` exacto | `?state=ACTIVE` |

Múltiples filtros se combinan con `AND`. Ejemplos:

```
GET /products/?state=ACTIVE&price=15.0
GET /users/?is_active=true&first_name=admin
GET /shelves/?aisle=A&row=1
GET /events/?action=CREATE&entity_type=Product
```

Campos seriales documentados en Swagger: `barcode` (products), `email` (users), `code` (shelves), `name` (roles).

Campos bloqueados: `hashed_password` en users (ignorado por seguridad).

## RBAC — Roles y Permisos

**Tablas:** `permissions`, `roles`, `role_permissions` (n-m), `user_roles` (n-m, usuario con N roles).

**Códigos** definidos en `app/core/permissions.py` (`PermissionCode` enum):
`products_create`, `products_read`, `products_update`, `products_delete`, `events_read`, `roles_manage`, `users_manage`, `shelves_create`, `shelves_read`, `shelves_update`, `shelves_delete`

**Seed inicial** (`app/seed.json` → `app/core/seed.py`):

| Rol | Permisos |
|-----|----------|
| `Admin` | todos (11 permisos) |
| `Operator` | products_create, products_read, products_update, shelves_read, shelves_update |
| `Viewer` | products_read, shelves_read |

**`require_permission(code)`** (`app/core/security.py`) — dependencia inyectable:
- `is_super_admin=True` → bypass total
- Query: User → UserRole → RolePermission → Permission
- Sin permiso → 403

## Auditoría global

`AuditLogger` (`app/core/audit.py`) inyectable vía `Depends(get_audit_logger)`. Serializa automáticamente Pydantic schemas, SQLAlchemy entities (vía `class_mapper`) y dicts. Filtra `hashed_password`.

```python
await self.audit.log_create("Product", product.id, user_id, product)
await self.audit.log_update("Product", product.id, user_id, product_in)
await self.audit.log_status_change("Product", id, user_id, old, new)
await self.audit.log_delete("Product", product.id, user_id, product)
```

## Seguridad

### Autenticación
- **bcrypt** para hashing de contraseñas con salt automático
- **JWT HS256** con `SECRET_KEY` (mín. 32 caracteres validado al iniciar)
- **Token version** — al cambiar contraseña se invalida la sesión de todos los dispositivos
- **Rate limit** por IP: 1000 req/60s global, 5 req/60s en forgot-password, 10 req/60s en activate

### Protección de datos
- `hashed_password` excluido de filtros genéricos (`__filterable_skip__`) y del audit log
- Tokens de reset/activación hasheados con SHA-256 en BD (nunca se almacena el token crudo)
- **Mitigación de timing attack** en forgot-password con delay aleatorio cuando el email no existe
- Campos string con `max_length` en schemas Pydantic (previene overflow y limita surface de ataque)
- **Límite de body size**: 10MB por defecto (`REQUEST_BODY_MAX_SIZE_MB`), retorna 413 si se excede

### Upload de archivos
- Validación de tipo MIME: solo JPEG, PNG, WebP, GIF, SVG
- Nombres generados con UUID (previene path traversal)
- Límite de 10MB por archivo
- Al eliminar entidad se borra su imagen del storage

### Headers de seguridad
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`  
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Cache-Control: no-store, max-age=0`

### RBAC
- `require_permission(code)` — dependencia inyectable en todas las rutas protegidas
- `is_super_admin=True` — bypass total de permisos
- Validación en capa de ruta (no en servicio): si no tiene permiso → 403

### Docker
- **Multi-stage build**: herramientas de compilación (gcc, libpq-dev) solo en stage builder
- `.dockerignore` excluye `.env`, `.git`, `venv/`, `__pycache__`, etc.
- PostgreSQL no expuesto al host en producción (mapeo de puertos comentable)

### Logging
- `logging` estructurado en lugar de `print()` (main, email, servicios)
- No se loguean contraseñas ni datos sensibles
- Formato: `timestamp [LEVEL] module: message`

## Almacenamiento de imágenes

Storage abstraction con adapter pattern (`app/core/storage.py`):

- `StorageBackend(ABC)` — interfaz `upload` / `delete`
- `LocalStorageBackend` — guarda en `static/uploads/` (nombrado: `{prefix}_{uuid}.{ext}`)
- `S3StorageBackend` — futuro, configurable vía `STORAGE_BACKEND=s3`

Imágenes se sirven vía `StaticFiles` montado en `/static`. Respuesta JSON incluye `image_url` computado (`/static/uploads/...`).

Al eliminar un producto/usuario, su imagen se borra del disco automáticamente.

## Validación de capacidad (estanterías)

Al asignar un producto a una estantería se validan tres reglas:

1. **Dimensiones:** cada dimensión del producto (`width_cm`, `height_cm`, `depth_cm`) debe ser ≤ la dimensión de la estantería. Solo si el valor de la estantería es > 0.
2. **Peso:** Σ(producto.weight_kg × item.quantity) ≤ shelf.max_weight_kg. Solo si max_weight_kg > 0.
3. **Volumen:** total_volume (existing_volume + product_volume × quantity) ≤ shelf_volume (width × height × depth). Solo si shelf_volume > 0 (todas las dimensiones > 0).

Además se valida **stock**: Σ(quantity asignada en todas las estanterías) + nueva_cantidad ≤ product.stock.

Error → `400 Bad Request` con detalle de todas las validaciones fallidas concatenadas con `"; "`.

**POST /items upsert:** Si el producto ya existe en la estantería, se suma la cantidad a la existente en vez de devolver 409. Se validan capacidad y stock para el nuevo total. Si alguna validación falla, no se modifica nada.

La respuesta de detalle (`GET /shelves/{id}`) incluye `current_weight_kg` (peso total) y `current_volume_cm3` (volumen total ocupado).

## Modelos

### User

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | int | PK |
| `email` | str(255) | único, indexado |
| `hashed_password` | str(255) | bcrypt, bloqueado en filtros |
| `first_name` | str\|null | |
| `last_name` | str\|null | |
| `phone` | str\|null | |
| `city` | str\|null | |
| `country` | str\|null | |
| `is_active` | bool | default true |
| `is_super_admin` | bool | bypass permisos, default false |
| `image_path` | str(500)\|null | ruta relativa en storage |
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
| `barcode` | str(128)\|null | único, indexado, setter convierte "" → null |
| `image_path` | str(500)\|null | ruta relativa en storage |
| `weight_kg` | float | `max(0)`, ge=0 |
| `width_cm` | float | `max(0)`, ge=0 |
| `height_cm` | float | `max(0)`, ge=0 |
| `depth_cm` | float | `max(0)`, ge=0 |
| `create_at` | datetime | server_default now() |
| `update_at` | datetime | onupdate now() |

Máquina de estados: stock=0 → NO_STOCK, stock>0 + NO_STOCK → ACTIVE.

### Shelf

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | int | PK |
| `name` | str(100) | nombre descriptivo |
| `code` | str(50) | único (ej: "A-01-03") |
| `aisle` | str(20) | pasillo |
| `row` | int | fila |
| `level` | int | nivel |
| `max_weight_kg` | float | capacidad peso (0=sin límite) |
| `width_cm` | float | ancho (0=sin límite) |
| `height_cm` | float | alto (0=sin límite) |
| `depth_cm` | float | fondo (0=sin límite) |
| `created_at` | datetime | server_default now() |
| `updated_at` | datetime | onupdate now() |

### ShelfItem (pivote n-m)

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | int | PK |
| `shelf_id` | int | FK → shelves (CASCADE) |
| `product_id` | int | FK → products (CASCADE) |
| `quantity` | int | cantidad en esta estantería |

UniqueConstraint: `(shelf_id, product_id)` — mismo producto no puede estar dos veces en la misma estantería.

### Event

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | int | PK |
| `entity_type` | str(100) | "Product", "User", "Shelf", ... |
| `entity_id` | int | |
| `action` | enum | CREATE\|UPDATE\|DELETE\|STATUS_CHANGED |
| `user_id` | int | FK users, indexado |
| `description` | str\|null | JSON |
| `create_at` | datetime | server_default now() |

Índice compuesto: `(entity_type, entity_id)`.

### Role y Permission (sin cambios)

| Role | | Permission | |
|------|-|------------|-|
| `id` | int PK | `id` | int PK |
| `name` | str(100) único | `code` | str(100) único |
| `description` | str\|null | `description` | str\|null |
| `created_at` | datetime | | |
| `updated_at` | datetime | | |

## Variables de entorno

| Variable | Default | Descripción |
|----------|---------|-------------|
| `DATABASE_URL` | *(requerido)* | postgresql://user:pass@host:5432/db |
| `SECRET_KEY` | *(requerido)* | JWT signing key (mín. 32 caracteres) |
| `ADMIN_EMAIL` | *(vacío)* | Email del admin creado en primer arranque |
| `ADMIN_PASSWORD` | *(vacío)* | Password del admin (si no se define, no se crea admin) |
| `API_V1_STR` | `/api/v1` | Prefijo API |
| `PROJECT_NAME` | `LogisticSystem` | Título docs |
| `ACCESS_TOKEN_EXPIRE_HOURS` | `24` | Expiración JWT |
| `CORS_ORIGINS` | `["*"]` cuando vacío | Orígenes permitidos (JSON array). Vacío = `*` sin credenciales. Con orígenes explícitos: habilita credenciales. |
| `APP_PORT` | `8000` | Puerto HTTP |
| `RATE_LIMIT_REQUESTS` | `1000` | Requests por ventana (0=deshabilitado) |
| `RATE_LIMIT_WINDOW` | `60` | Ventana en segundos |
| `REQUEST_BODY_MAX_SIZE_MB` | `10` | Tamaño máximo del body (MB) |
| `STORAGE_BACKEND` | `local` | `local` o `s3` |
| `STORAGE_PATH` | `static/uploads` | Directorio base local |
| `S3_BUCKET` | *(vacío)* | Bucket S3 |
| `S3_REGION` | `auto` | Región S3 |
| `S3_ACCESS_KEY` | *(vacío)* | Access key S3 |
| `S3_SECRET_KEY` | *(vacío)* | Secret key S3 |
| `S3_ENDPOINT` | *(vacío)* | Endpoint S3 personalizado |
| `S3_PUBLIC_URL` | *(vacío)* | URL pública para assets S3 |
| `RESEND_API_KEY` | *(vacío)* | API key de Resend (email) |
| `RESEND_FROM_EMAIL` | `noreply@logisticsystem.com` | Remitente emails |
| `PASSWORD_RESET_TOKEN_EXPIRE_MINUTES` | `30` | Expiración token reset password |
| `ACCOUNT_ACTIVATION_EXPIRE_HOURS` | `24` | Expiración token activación |
| `FRONTEND_URL` | `http://localhost:5173` | URL del frontend para links de email |

## Transacciones y Migraciones

- **Transacciones:** `get_db` hace commit al final del request, rollback en excepción. `Base` usa `flush` (no `commit`).
- **Migraciones:** Alembic ejecutado en `start.sh` al iniciar (`alembic upgrade head`). Generar nuevas: `python -m alembic revision --autogenerate -m "descripción"`.

## Seed

`app/seed.json` define permisos y roles iniciales. `app/core/seed.py` lo carga al primer arranque (idempotente: solo corre si tabla permissions vacía). Si se configuran `ADMIN_EMAIL` y `ADMIN_PASSWORD`, crea un usuario admin super_admin con rol Admin. Para agregar permisos/roles: editar seed.json + `app/core/permissions.py`.

`scripts/seed_electrodomesticos.py` — seed masivo standalone: 200 productos, 200 estanterías, 200 usuarios con roles variados. Usa acceso directo a DB para velocidad.

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

Registrar router en `app/api/v1/api.py`. Importar modelo en `alembic/env.py`. Si requiere filtros: heredar de `Base` (ya incluye `get_all` con `filters` param).
