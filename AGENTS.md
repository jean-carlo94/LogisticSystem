# AGENTS.md - LogisticSystem API

## Commands

```bash
# Dev (local, needs PostgreSQL)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Docker (standalone, preferred)
docker compose up --build -d
docker compose down -v   # (destruye volúmenes, DB fresca)
```

No test suite, linter, formatter, or typechecker. `.gitignore` excludes `venv/` and `.env`.

## Architecture

```
app/
├── main.py                   # FastAPI app, lifespan (seed), CORS, StaticFiles, exception handler
├── seed.json                 # Seed inicial de permisos + roles
├── core/
│   ├── config.py             # pydantic-settings con @lru_cache
│   ├── database.py           # async engine lazy + AsyncSession + Base (CRUD + filtros)
│   ├── security.py           # JWT + bcrypt + get_current_user + require_permission
│   ├── audit.py              # AuditLogger (serializa Pydantic/SQLAlchemy/dict)
│   ├── pagination.py         # PaginatedResult + PaginatedResponse + PaginationParams + FilterParams
│   ├── storage.py            # StorageBackend ABC + LocalStorageBackend (S3 futuro)
│   ├── permissions.py        # PermissionCode enum (constantes de permisos)
│   ├── exceptions.py         # AppException + NotFound/Conflict/Forbidden/Unauthorized/BadRequest/Validation
│   ├── repository.py         # BaseRepository ABC
│   └── seed.py               # Carga seed.json → DB + admin default (primer arranque)
├── api/
│   ├── dependencies.py       # get_audit_logger (dependencias compartidas)
│   └── v1/api.py             # Registro de routers
└── modules/
    ├── products/             # CRUD + state machine (ProductState) + images + QR + barcode + dimensions
    ├── events/               # Audit log append-only (ActionType)
    ├── users/                # Auth + profile + image + admin CRUD
    ├── roles/                # CRUD roles, permisos, asignaciones
    └── shelves/              # CRUD estanterías + items + validación capacidad
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
# ❌ Service accessing db directly
result = await self.repo.db.scalars(select(...))

# ❌ Router injecting multiple services from different modules
def endpoint(service_a: ServiceA, service_b: ServiceB): ...

# ❌ Router calling model/repository directly
def endpoint(db: Session = Depends(get_db)): ...

# ❌ Service importing from another module's service (creates coupling)
from app.modules.roles.service import RoleService
```

### ALLOWED patterns

```python
# ✅ Service calls repo method
roles = await self.repo.get_user_roles(user_id)

# ✅ Service calls model classmethod (via repo or directly for cross-model lookups)
if not await self.repo.role_exists(role_id): ...

# ✅ Router only depends on ONE service from its own module
def endpoint(service: MyService = Depends(get_my_service)): ...

# ✅ Cross-module access only through repository or model classmethods
# If UserService needs Role data → add method to UserRepository
```

## Key conventions

- **Tables auto-created** via Alembic migrations on startup (`alembic upgrade head` in `start.sh`). Generate migrations: `python -m alembic revision --autogenerate -m "desc"`.
- **Dependency injection** via FastAPI `Depends`. Each module has `deps.py` factories wiring repos → services.
- **Module boilerplate**: create `model.py` → `schema.py` → `repository.py` (extends `BaseRepository`) → `service.py` → `router.py` → `deps.py`, register router in `app/api/v1/api.py`, import model in `alembic/env.py`.
- **Base CRUD** (`app/core/database.py`): `get_id`, `get_all`, `create`, `save`, `update`, `delete`. Uses `setattr` for auto-triggering property setters.
- **BaseRepository** (`app/core/repository.py`): ABC with `model: type[Base]`. Provides `get_all`, `get_by_id`, `create`, `update`, `delete`.
- **Property setters**: Model properties (e.g., `name.strip()`, `price.round(2)`, `stock.max(0)`, `weight_kg.max(0)`) auto-triggered via `Base._new()` and `Base.update()` using `setattr`. No manual `__init__` needed.
- **Product state machine** (`app/modules/products/service.py:_resolve_state`): stock=0 → NO_STOCK, stock>0 + current NO_STOCK → ACTIVE, else leave as-is.
- **Events append-only**: GET only. Written via `AuditLogger` inside services. Generic: `entity_type + entity_id + user_id + action`.
- **Audit logging**: `AuditLogger` (`app/core/audit.py`) serializes Pydantic schemas, SQLAlchemy entities (via `class_mapper`), dicts. Filters `hashed_password`. Injected via `Depends(get_audit_logger)`.
- **RBAC**: `PermissionCode` enum in `app/core/permissions.py`. `require_permission(code)` dependency in routes. `is_super_admin=True` bypasses all checks. Seed in `app/seed.json`.
- **Transactions**: `get_db` commits on success, rolls back on exception. `Base` methods use `flush` (not commit). Request-scoped atomicity.
- **Async**: `AsyncSession` + `async def` en todas las capas (router, service, repository, Base).
- **Pagination**: `PaginationParams = Depends(get_pagination)` for query params. Return type `PaginatedResponse[T]`.
- **Exceptions**: Custom `AppException` subclasses (`NotFoundException`, `ConflictException`, `ValidationException`, etc.). Global handler in `main.py`. Services NEVER raise `HTTPException`.
- **Env vars**: `DATABASE_URL` (required), `SECRET_KEY` (required). Others have defaults. `.env` gitignored; `.env.example` exists.
- **Imports**: Use `from __future__ import annotations` + `TYPE_CHECKING` for cross-module type hints to prevent circular imports.

## Filters (GENÉRICOS)

`Base.get_all` acepta `filters: dict | None`. Todos los campos de cualquier modelo son filtrables automáticamente.

```python
@classmethod
async def get_all(cls, db, skip=0, limit=100, order_by=None, filters: dict | None = None)
```

- **Strings/Text** → `ILIKE %value%` (case-insensitive, búsqueda parcial)
- **Integer/Float/Boolean/Enum** → `==` exacto con type coercion automática
- **Propiedades con setter** (ej: `name`, `price`, `stock`) → se resuelven al atributo privado (`_name`, `_price`, `_stock`) vía `_resolve_filter_column()`
- **`__filterable_skip__`** → set de campos a ignorar (ej: `{"hashed_password"}` en User)
- **`__created_at_attr__`** → atributo para orden default desc (ej: `"created_at"` o `"create_at"`)
- **Coerción de tipos** en `_coerce_filter_value()`: String/Text → str, Integer → int(), Float → float(), Boolean → bool, Enum → enum_class(value)
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
async def get_all(self, page=1, size=20, filters: dict | None = None) -> PaginatedResult[MyModel]:
    skip = (page - 1) * size
    items, total = await self.repo.get_all(skip=skip, limit=size, filters=filters)
    return PaginatedResult.of(list(items), total, page, size)
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
```

- Archivos guardados en `static/uploads/{entity}/{prefix}_{uuid}.{ext}`
- Servidos vía `StaticFiles` en `main.py`: `app.mount("/static", StaticFiles(...))`
- `image_url` en responses es campo computado vía `@model_validator(mode="after")`
- `python-multipart` requerido para file uploads

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

Errores múltiples se concatenan con `"; "`. Al actualizar cantidad (PUT item) se excluye el propio peso del item para evitar doble conteo.

- `ShelfItem` tiene UniqueConstraint `(shelf_id, product_id)` → no puede haber dos asignaciones del mismo producto en la misma estantería
- Eliminar estantería solo si no tiene items → `ConflictException`

## Barcode (products)

- `Product.barcode`: String(128), unique=True, nullable=True, index=True
- Varios productos pueden tener `barcode=null`
- Si se envía `barcode` y ya existe otro producto con ese valor → `409 Conflict`
- Validación en create y update

## Dimensiones (products)

- `Product.weight_kg`, `width_cm`, `height_cm`, `depth_cm` → Float, default=0, clamp ≥0 vía property setter
- Solo se validan contra estantería cuando > 0 en ambos lados

## Seed + admin default

`app/core/seed.py` crea al primer arranque:
- Permisos y roles desde `seed.json`
- Usuario admin: `admin@logistics.com` / `admin123` (is_super_admin=True, asignado al rol Admin)

Idempotente: solo corre si tabla `permissions` está vacía.

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
