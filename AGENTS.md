# AGENTS.md - LogisticSystem API

## Commands

```bash
# Dev (local, needs PostgreSQL)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Docker dev (volume-mounted source, DB port exposed)
docker compose up --build -d
docker compose down -v   # (destruye volúmenes, DB fresca)

# Docker production (self-contained image, no DB port exposure)
cp .env.prod.example .env.prod   # editar con valores reales
docker compose -f docker-compose.prod.yml up --build -d
```

No test suite, linter, formatter, or typechecker. `.gitignore` excludes `venv/` and `.env`.

## Architecture

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
│   ├── permissions.py        # PermissionCode enum (constantes de permisos, incluye TENANTS_MANAGE)
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
    ├── tenants/              # CRUD tenants + creación de roles/admin por tenant
    ├── products/             # CRUD + state machine (ProductState) + images + QR + barcode + dimensions
    ├── events/               # Audit log append-only (ActionType, tenant_id nullable)
    ├── users/                # Auth + profile + image + admin CRUD (tenant_id nullable)
    ├── roles/                # CRUD roles por tenant, permisos globales, asignaciones
    ├── shelves/              # CRUD estanterías + items + validación capacidad
    ├── categories/           # CRUD categorías por tenant + asignación a productos
    ├── sales/                # Crear ventas, descuento de stock producto + estantería
    └── orders/               # Pedidos con state machine (CREATED→PREPARING→READY→DELIVERED) + entrega crea venta
```

### Layer chain (STRICT)

```
Router → Depends(deps.py) → Service → Repository → Base/Model
```

| Layer | File | Rules |
|-------|------|-------|
| **Router** | `router.py` | Only HTTP concerns. Calls service methods. NO business logic, NO DB access. |
| **Service** | `service.py` | Business logic + audit. Calls repository methods. **NEVER access `self.repo.db` directly.** |
| **Repository** | `repository.py` | Data access only. Extends `BaseRepository`. All queries here. |
| **Model** | `model.py` | ORM definition + class-level queries (`find_by_*`). Extends `Base`. |

### FORBIDDEN patterns

```python
# ❌ Service accessing db directly — this is the #1 violation
#    All DB access goes through repository methods, NEVER through repo.db
result = await self.repo.db.scalars(select(...))
product = await User.get_id(self.repo.db, user_id)

# ❌ Static helper in service that takes db as parameter — bypasses repository layer
@staticmethod
async def _get_product(db, product_id):  # ❌ service level, takes db directly
    return await db.scalar(select(Product).where(...))

# ❌ Inline SQLAlchemy imports in service (select, func, etc.)
#    These only belong in repository.py or model.py
from sqlalchemy import select  # ❌ in service.py

# ❌ Router injecting multiple services from different modules
def endpoint(service_a: ServiceA, service_b: ServiceB): ...

# ❌ Router calling model/repository directly
def endpoint(db: Session = Depends(get_db)): ...

# ❌ Service importing from another module's service (creates coupling)
#    Excepción: OrderService inyecta SaleService via deps.py para crear venta al entregar pedido.
#    Esto es intencional — duplicar lógica de venta sería peor que el acoplamiento.
from app.modules.roles.service import RoleService

# ❌ List endpoint without PaginationParams — pagination silently broken
@router.get("/")
async def list_items(
    filters: dict = FilterParams,  # has pagination? NO pag param!
    ...
):

# ❌ AuditLogger missing from service that does CRUD operations
class MyService:
    def __init__(self, repo):  # ❌ no audit parameter
        ...

# ❌ N+1 queries — loop over DB results issuing separate queries
for role in roles:
    perms = await self.db.scalars(select(...).where(role_id == role.id))  # ❌
```

### ALLOWED patterns

```python
# ✅ Service calls repo method
roles = await self.repo.get_user_roles(user_id)

# ✅ Cross-module data access through repository — add the method there
# Shelf service needs Product data → add method to ShelfItemRepository
product = await self.item_repo.get_product_by_id(product_id)

# ✅ Cross-module access through repository (not service!)
# RoleRepository needs to check if user exists → add to UserRoleRepository
if not await self.user_role_repo.user_exists(user_id): ...

# ✅ Router only depends on ONE service from its own module
def endpoint(service: MyService = Depends(get_my_service)): ...

# ✅ All list endpoints MUST include PaginationParams
@router.get("/", response_model=PaginatedResponse[MyResponse])
async def list_items(
    pag: dict = PaginationParams,        # ✅ REQUIRED
    filters: dict = FilterParams,        # ✅ for generic filters
    ...
):
    return await service.get_all(page=pag["page"], size=pag["size"], ...)

# ✅ Service with AuditLogger for any create/update/delete operations
class MyService:
    def __init__(self, repo: MyRepo, audit: AuditLogger):  # ✅
        self.repo = repo
        self.audit = audit

# ✅ Bulk queries with IN clause — never loop to fetch individual records
role_ids = [r.id for r in roles]
all_perms = await self.db.scalars(select(...).where(col.in_(role_ids)))  # ✅

# ✅ Property setters for string fields that need sanitization
_name: Mapped[str] = mapped_column("name", ...)
@property
def name(self) -> str:
    return self._name
@name.setter
def name(self, value: str):
    self._name = value.strip()  # ✅
```

## Key conventions

- **Tables auto-created** via Alembic migrations on startup (`alembic upgrade head` in `start.sh`). Generate migrations: `python -m alembic revision --autogenerate -m "desc"`.
- **Dependency injection** via FastAPI `Depends`. Each module has `deps.py` factories wiring repos → services.
- **Module boilerplate**: create `model.py` → `schema.py` → `repository.py` (extends `BaseRepository`) → `service.py` → `router.py` → `deps.py`, register router in `app/api/v1/api.py`, import model in `alembic/env.py`.
- **Base CRUD** (`app/core/database.py`): `get_id`, `get_all`, `create`, `save`, `update`, `delete`. Uses `setattr` for auto-triggering property setters.
- **BaseRepository** (`app/core/repository.py`): ABC with `model: type[Base]`. Provides `get_all`, `get_by_id`, `create`, `update`, `delete`.
- **Property setters**: Model properties (e.g., `name.strip()`, `price.round(2)`, `stock.max(0)`, `weight_kg.max(0)`) auto-triggered via `Base._new()` and `Base.update()` using `setattr`. No manual `__init__` needed.
- **Product state machine** (`app/modules/products/service.py:_resolve_state`): stock=0 → NO_STOCK, stock>0 + current NO_STOCK → ACTIVE, else leave as-is.
- **Order state machine** (`app/modules/orders/service.py`): CREATED → PREPARING → READY → DELIVERED. Solo forward. Cada transición es un endpoint separado (`POST /orders/{id}/prepare`, `/ready`, `/deliver`). Al hacer `deliver`, `OrderService` crea automáticamente una venta via `SaleService.create()`. `SaleService` se inyecta en `OrderService` vía `deps.py` (excepción intencional a la regla de no acoplar servicios).
- **Orders shelf optional**: `OrderItem.shelf_id` es nullable. Si se especifica, valida que el producto esté asignado a esa estantería y con stock suficiente. Si no, solo valida producto + stock general. Al entregar, la venta resultante respeta el `shelf_id` (o lo omite) del pedido original.
- **Events append-only**: GET only. Written via `AuditLogger` inside services. Generic: `entity_type + entity_id + user_id + action`.
- **Audit logging**: `AuditLogger` (`app/core/audit.py`) serializes Pydantic schemas, SQLAlchemy entities (via `class_mapper`), dicts. Filters `hashed_password`. Injected via `Depends(get_audit_logger)`.
- **RBAC**: `PermissionCode` enum in `app/core/permissions.py`. `require_permission(code)` dependency in routes. `is_super_admin=True` bypasses all checks. Seed in `app/seed.json`.
- **Transactions**: `get_db` commits on success, rolls back on exception. `Base` methods use `flush` (not commit). Request-scoped atomicity.
- **Async**: `AsyncSession` + `async def` en todas las capas (router, service, repository, Base).
- **Pagination**: `PaginationParams = Depends(get_pagination)` for query params. Return type `PaginatedResponse[T]`.
- **Exceptions**: Custom `AppException` subclasses (`NotFoundException`, `ConflictException`, `ValidationException`, etc.). Global handler in `main.py`. Services NEVER raise `HTTPException`.
- **Env vars**: Todas las settings sin default hardcodeado — deben definirse en `.env` o env vars del sistema. Solo `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `RESEND_API_KEY` tienen default vacío (opcionales reales). `.env` gitignored; `.env.example` y `.env.prod.example` existen.
- **Rate limit**: 1000 requests per 60s window (configurable via `RATE_LIMIT_REQUESTS`, set to 0 to disable). Returns 429 `"Demasiadas solicitudes. Intenta de nuevo mas tarde."` per client IP. Endpoints forgot-password (5/min) y activate (10/min) tienen limiters independientes. In-memory, single-worker only.
- **Imports**: Use `from __future__ import annotations` + `TYPE_CHECKING` for cross-module type hints to prevent circular imports.
- **Logging**: `logging` estructurado (`logging.getLogger(__name__)`) en lugar de `print()`. Configurado en `main.py` con `logging.basicConfig`.
- **Security headers**: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection`, `Referrer-Policy`, `Cache-Control` aplicados en middleware HTTP.
- **Body size limit**: `REQUEST_BODY_MAX_SIZE_MB` (default 10). Retorna 413 si `content-length` excede el límite.
- **SECRET_KEY**: Validación de longitud mínima 32 caracteres vía `@field_validator` en Settings.
- **Admin seed**: Credenciales vía `ADMIN_EMAIL`/`ADMIN_PASSWORD` env vars. Si no se definen, usa fallback `admin@alunatechnologies.com` / `admin123`. `is_super_admin=True`, sin `tenant_id`.
- **Docker**: Multi-stage build (gcc/libpq-dev solo en stage builder). `.dockerignore` excluye `.env`, `.git`, `venv/`, etc.
- **CORS**: `CORS_ORIGINS` (list[str] en JSON). Vacío = `allow_origins=["*"]` sin credenciales. Con orígenes explícitos → `allow_credentials=True` y `Access-Control-Allow-Credentials: true`. Si el frontend usa `credentials: 'include'` o `Authorization`, configurar orígenes explícitos: `CORS_ORIGINS=["http://localhost:5173"]`. Pasar como env var en docker-compose para que no dependa solo del archivo `.env`.

## Multitenant

Schema compartido (misma DB) con columna `tenant_id` en tablas de negocio. Aislamiento automático vía `ContextVar`.

### Modelo de datos

**Tablas con `tenant_id`:**
`users` (nullable, null = platform admin), `products`, `categories`, `shelves`, `sales`, `orders`, `events` (nullable), `roles`.

**Sin `tenant_id`** (scoped via FK padre): `shelf_items`, `sale_items`, `order_items`, `product_categories`, `role_permissions`, `user_roles`, `permissions` (global).

**Unique constraints compuestos:** `(tenant_id, barcode)` en products, `(tenant_id, code)` en shelves, `(tenant_id, name)` en categories y roles. `email` se mantiene unique global.

### Tenant context (ContextVar)

```python
# app/core/tenant.py
current_tenant_id: ContextVar[int | None] = ContextVar("current_tenant_id", default=None)
```

**Resolución automática:**
1. `get_current_user` setea `current_tenant_id` para usuarios con tenant
2. `_tenant_context` (interno de `require_permission`) maneja header `X-Tenant: <slug>` para platform admins
3. `BaseRepository` lee `current_tenant_id` en cada método (property lazy, no en `__init__`)
4. `Base.get_all/get_id` aplican `WHERE tenant_id = :tid` si el modelo tiene la columna y el context no es None
5. `BaseRepository.create` auto-inyecta `tenant_id` en kwargs si no se pasó explícitamente

**Platform admin:**
- Sin `X-Tenant` → `current_tenant_id = None` → ve TODOS los tenants
- Con `X-Tenant: <slug>` → switchea a ese tenant para soporte/configuración

### Creación de tenant

`POST /tenants` (`TENANTS_MANAGE`):
1. Crea registro en tabla `tenants`
2. `seed_tenant_roles(tenant.id)` — crea roles Admin/Operator/Viewer para ese tenant con permisos del `seed.json`
3. Si se envían `admin_email` + `admin_password` → crea usuario admin con `tenant_id` y rol Admin

### JWT

`create_access_token` incluye `tid` (tenant_id) en el payload. `create_access_token(user.id, user.token_version, user.tenant_id)`.

### Eventos (audit)

`AuditLogger._log` lee `current_tenant_id` del ContextVar. `events.tenant_id` es nullable (operaciones platform-level como crear tenant no tienen tenant context).

### PermissionCode

`TENANTS_MANAGE = "tenants_manage"` — solo platform admin (`is_super_admin=True`). Roles por tenant NO incluyen este permiso.

### FORBIDDEN / ALLOWED patterns

```python
# ❌ Leer current_tenant_id en __init__ del repositorio
class MyRepo(BaseRepository):
    def __init__(self, db):
        self._tenant_id = current_tenant_id.get()  # ❌ aún no se resolvió!

# ✅ Leer current_tenant_id lazy (property)
class BaseRepository:
    @property
    def _tenant_id(self):
        return current_tenant_id.get()  # ✅ resuelto al momento del query

# ❌ Usar propiedad Python en queries SQL
stmt = select(Role).where(Role.name == "Admin")    # ❌ Role.name es @property
# ✅ Usar el atributo privado (columna real)
stmt = select(Role).where(Role._name == "Admin")    # ✅ Role._name es la columna

# ❌ Pasar tenant_id explícito desde BaseRepository.create si ya está en kwargs
async def create(self, **kwargs):
    return await self.model.create(self.db, tenant_id=self._tenant_id, **kwargs)  # ❌ duplicado
# ✅ Solo inyectar si no viene en kwargs
async def create(self, **kwargs):
    tid = self._tenant_id
    if tid is not None and hasattr(self.model, "tenant_id") and "tenant_id" not in kwargs:
        kwargs["tenant_id"] = tid
    return await self.model.create(self.db, **kwargs)
```

## Filters (GENÉRICOS)

`Base.get_all` acepta `filters: dict | None`. Todos los campos de cualquier modelo son filtrables automáticamente. `tenant_id` se excluye automáticamente de los filtros de query params.

```python
@classmethod
async def get_all(cls, db, skip=0, limit=100, order_by=None, filters: dict | None = None)
```

- **Strings/Text** → `ILIKE %value%` (case-insensitive, búsqueda parcial)
- **Integer/Float/Boolean/Enum** → `==` exacto con type coercion automática
- **DateTime/Date** → Range día exacto `>= date AND < date+1d` (formato `YYYY-MM-DD`). Vía `_is_date_column()`.
- **Propiedades con setter** (ej: `name`, `price`, `stock`) → se resuelven al atributo privado (`_name`, `_price`, `_stock`) vía `_resolve_filter_column()`
- **`__filterable_skip__`** → set de campos a ignorar (ej: `{"hashed_password"}` en User)
- **`__created_at_attr__`** → atributo para orden default desc (ej: `"created_at"` o `"create_at"`)
- **Coerción de tipos** en `_coerce_filter_value()`: String/Text → str, Integer → int(), Float → float(), Boolean → bool, Enum → enum_class(value), DateTime → date (YYYY-MM-DD)
- Valores que no se pueden convertir se ignoran (retornan `None` y no aplican el where)

### Router pattern para filtros

```python
from app.core.pagination import FilterParams, PaginationParams

@router.get("/", response_model=PaginatedResponse[MyResponse])
async def list_items(
    pag: dict = PaginationParams,
    filters: dict = FilterParams,    # captura TODOS los query params (excepto page/size)
    service: MyService = Depends(get_my_service),
    _perm = Depends(require_permission(PermissionCode.MY_READ)),
):
    return await service.get_all(page=pag["page"], size=pag["size"], filters=filters or None)
```

Para documentar campos seriales en Swagger, agregar Query params explícitos y mergear:

```python
async def list_items(
    pag: dict = PaginationParams,
    code: str | None = Query(default=None, description="Código único"),
    filters: dict = FilterParams,
    ...
):
    merged = dict(filters)
    if code is not None:
        merged["code"] = code
    return await service.get_all(page=pag["page"], size=pag["size"], filters=merged or None)
```

### Service pattern para filtros

```python
async def get_all(self, page=1, size=20, filters: dict | None = None) -> PaginatedResponse[MyModel]:
    skip = (page - 1) * size
    items, total = await self.repo.get_all(skip=skip, limit=size, filters=filters)
    return PaginatedResponse.of(list(items), total, page, size)
```

## Storage (imágenes)

`app/core/storage.py` — adapter pattern para archivos:

```python
class StorageBackend(ABC):
    async def upload(file: UploadFile, relative_path: str) -> str
    async def delete(relative_path: str) -> None

class LocalStorageBackend(StorageBackend): ...
# class S3StorageBackend(StorageBackend): ...  (futuro)

def get_storage() -> StorageBackend
def generate_filename(prefix: str, original_filename: str) -> str
def validate_file(file: UploadFile) -> None  # MIME type validation
```

- Archivos guardados en `static/uploads/{entity}/{prefix}_{uuid}.{ext}`
- Servidos vía `StaticFiles` en `main.py`: `app.mount("/static", StaticFiles(...))`
- `image_url` en responses es campo computado vía `@model_validator(mode="after")`
- `python-multipart` requerido para file uploads
- **Validación MIME**: solo JPEG, PNG, WebP, GIF, SVG (`ALLOWED_IMAGE_TYPES` + `ALLOWED_IMAGE_EXTENSIONS`). Validado por `validate_file()` antes del upload.
- **Límite 10MB** por archivo (`MAX_FILE_SIZE` en storage.py). También hay límite global de body (`REQUEST_BODY_MAX_SIZE_MB`).
- Nombres de archivo generados con UUID para prevenir path traversal.

## Image handling (products + users)

**Flow:**
1. `POST /{entity}/{id}/image` → multipart/form-data campo `file`
2. Service llama `get_storage().upload()` → guarda archivo → actualiza `image_path` en DB
3. Si ya existía imagen anterior → la borra del disco antes de guardar la nueva
4. `DELETE /{entity}/{id}/image` → borra archivo del disco → limpia `image_path` a `None`
5. Al eliminar entidad → borra su imagen asociada del disco

## QR (products)

`GET /products/{id}/qr` → JSON (no imagen). Frontend renderiza QR.

```python
class ProductQRResponse(BaseModel):
    product_id: int
    name: str
    barcode: str | None
    shelf: ShelfInfo | None   # code, aisle, row, level
```

`shelf` es `null` si el producto no está asignado a estantería. Si está en múltiples, devuelve el primero.

## Shelves — validación de capacidad

```python
class ValidationException(AppException):  # 400
```

Al asignar/actualizar item en estantería (`ShelfService._validate_capacity`):

1. **Dimensiones:** producto.width_cm ≤ shelf.width_cm (solo si shelf > 0), igual para height y depth
2. **Peso:** Σ(producto.weight_kg × item.quantity) ≤ shelf.max_weight_kg (solo si > 0)
3. **Volumen:** total_volume (existing_volume + product_volume × quantity) ≤ shelf_volume (width × height × depth). Solo si shelf_volume > 0 (las 3 dimensiones > 0).

Errores múltiples se concatenan con `"; "`. Al actualizar cantidad (PUT item / upsert POST) se excluye el propio item del peso y volumen para evitar doble conteo, vía `_get_total_weight` y `_get_total_volume` con `exclude_item_id`.

### Shelves — validación de stock

`ShelfService._validate_stock(product_id, quantity, exclude_item_id=None)`:

- Obtiene `assigned = Σ(quantity)` de todos los items del producto en TODAS las estanterías (`ShelfItemRepository.get_items_by_product`)
- En upsert (POST a item existente) y PUT update_item, excluye el propio item vía `exclude_item_id`
- Valida: `assigned + quantity ≤ product.stock`
- Error: `"Stock insuficiente: {stock} en inventario, {assigned} ya asignados, {quantity} solicitados = {total} total"`

### Shelves — POST /items upsert

Si el producto ya existe en la estantería → en vez de devolver 409, suma la cantidad a la existente (`existing.quantity + data.quantity`). Valida capacidad Y stock para la nueva cantidad total. Si alguna validación falla, no se modifica nada.

- `ShelfItem` tiene UniqueConstraint `(shelf_id, product_id)` → no puede haber dos asignaciones del mismo producto en la misma estantería
- Eliminar estantería solo si no tiene items → `ConflictException`

### ShelfItemRepository

```python
class ShelfItemRepository(BaseRepository):  # ✅ extends BaseRepository
    async def get_by_id(item_id) -> ShelfItem | None
    async def get_by_shelf_product(shelf_id, product_id) -> ShelfItem | None
    async def get_items_by_shelf(shelf_id) -> list[ShelfItem]
    async def get_items_by_product(product_id) -> list[ShelfItem]  # usado en validación de stock
    async def get_product_by_id(product_id) -> Product | None      # cross-module, allowed in repo
    async def get_products_by_ids(product_ids) -> list[Product]     # bulk fetch para get_detail
```

### ShelfDetailResponse

```python
class ShelfDetailResponse(ShelfResponse):
    items: list[ShelfItemResponse] = []
    current_weight_kg: float = 0
    current_volume_cm3: float = 0  # Σ(product_volume × quantity) redondeado a 2 decimales
```

## Barcode (products)

- `Product.barcode`: String(128), unique constraint compuesto `(tenant_id, barcode)`, nullable=True, index=True
- Varios productos pueden tener `barcode=null`
- Si se envía `barcode` y ya existe otro producto con ese valor → `409 Conflict`
- Validación en create y update
- Property setter convierte empty string a `None` → evita violación de unique constraint por `""`

## Dimensiones (products)

- `Product.weight_kg`, `width_cm`, `height_cm`, `depth_cm` → Float, default=0, clamp ≥0 vía property setter
- Solo se validan contra estantería cuando > 0 en ambos lados

## Seed + admin default

`app/core/seed.py` crea al primer arranque:
- Permisos globales desde `seed.json` (idempotente, solo si tabla `permissions` vacía)
- Admin default con `ADMIN_EMAIL`/`ADMIN_PASSWORD` (usa fallback `admin@alunatechnologies.com` / `admin123`). `is_super_admin=True`, sin `tenant_id`.
- Los roles (Admin/Operator/Viewer) NO se crean globalmente — se crean por tenant via `seed_tenant_roles(tenant_id)` al llamar `POST /tenants`.

## DB engine (lazy)

`app/core/database.py` usa lazy initialization para el async engine. Esto evita errores de import en Alembic (que usa sync engine para migraciones).

```python
_async_engine = None

def _get_async_engine():
    global _async_engine
    if _async_engine is None:
        _async_engine = create_async_engine(...)
    return _async_engine
```

## Dependencies

```
requirements.txt:
  fastapi, uvicorn, sqlalchemy, alembic, pydantic-settings,
  psycopg2-binary, asyncpg, python-jose[cryptography], bcrypt,
  email-validator, python-multipart, aiofiles
```

`python-multipart` requerido para upload de archivos (File/UploadFile). `aiofiles` para servir estáticos async.
