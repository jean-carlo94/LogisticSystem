# AGENTS.md - LogisticSystem API

## Commands

```bash
# Dev (local, needs PostgreSQL)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Docker (standalone, preferred)
docker compose up --build -d
docker compose down
```

No test suite, linter, formatter, or typechecker. `.gitignore` excludes `venv/` and `.env`.

## Architecture

```
app/
├── main.py                   # FastAPI app, lifespan (seed), CORS, exception handler
├── seed.json                 # Seed inicial de permisos + roles
├── core/
│   ├── config.py             # pydantic-settings con @lru_cache
│   ├── database.py           # async engine + AsyncSession + Base (CRUD global)
│   ├── security.py           # JWT + bcrypt + get_current_user + require_permission
│   ├── audit.py              # AuditLogger (serializa Pydantic/SQLAlchemy/dict)
│   ├── pagination.py         # PaginatedResult + PaginatedResponse + PaginationParams
│   ├── permissions.py        # PermissionCode enum (constantes de permisos)
│   ├── exceptions.py         # AppException + NotFound/Conflict/Forbidden/Unauthorized
│   ├── repository.py         # BaseRepository ABC
│   └── seed.py               # Carga seed.json → DB (primer arranque)
├── api/
│   ├── dependencies.py       # get_audit_logger (dependencias compartidas)
│   └── v1/api.py             # Registro de routers
└── modules/
    ├── products/             # CRUD + state machine (ProductState)
    ├── events/               # Audit log append-only (ActionType)
    ├── users/                # Auth + profile + admin CRUD
    └── roles/                # CRUD roles, permisos, asignaciones
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
- **Property setters**: Model properties (e.g., `name.strip()`, `price.round(2)`) auto-triggered via `Base._new()` and `Base.update()` using `setattr`. No manual `__init__` needed.
- **Product state machine** (`app/modules/products/service.py:_resolve_state`): stock=0 → NO_STOCK, stock>0 + current NO_STOCK → ACTIVE, else leave as-is.
- **Events append-only**: GET only. Written via `AuditLogger` inside services. Generic: `entity_type + entity_id + user_id + action`.
- **Audit logging**: `AuditLogger` (`app/core/audit.py`) serializes Pydantic schemas, SQLAlchemy entities (via `class_mapper`), dicts. Filters `hashed_password`. Injected via `Depends(get_audit_logger)`.
- **RBAC**: `PermissionCode` enum in `app/core/permissions.py`. `require_permission(code)` dependency in routes. `is_super_admin=True` bypasses all checks. Seed in `app/seed.json`.
- **Transactions**: `get_db` commits on success, rolls back on exception. `Base` methods use `flush` (not commit). Request-scoped atomicity.
- **Async**: `AsyncSession` + `async def` en todas las capas (router, service, repository, Base).
- **Pagination**: `PaginationParams = Depends(get_pagination)` for query params. Return type `PaginatedResponse[T]`.
- **Exceptions**: Custom `AppException` subclasses (`NotFoundException`, `ConflictException`, etc.). Global handler in `main.py`. Services NEVER raise `HTTPException`.
- **Env vars**: `DATABASE_URL` (required), `SECRET_KEY` (required). Others have defaults. `.env` gitignored; `.env.example` exists.
- **Imports**: Use `from __future__ import annotations` + `TYPE_CHECKING` for cross-module type hints to prevent circular imports.
