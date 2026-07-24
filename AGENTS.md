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
├── main.py              # FastAPI app, lifespan (creates tables), CORS, root/health routes
├── core/
│   ├── config.py        # pydantic-settings from .env
│   ├── database.py      # engine, sessionmaker, Base, get_db generator
│   ├── pagination.py    # PaginatedResult + PaginatedResponse (page/size query params)
│   └── security.py      # JWT auth, password hashing, get_current_user dependency
├── api/v1/api.py        # Aggregates products + events + users routers under /api/v1 prefix
└── modules/
    ├── products/        # CRUD + state enforcement → ProductState enum
    ├── events/          # Audit log → ActionType enum (generic: entity_type+entity_id+user_id)
    └── users/           # User registration + login, JWT auth → /auth prefix
```

Layer chain: `router → Depends(deps.py factory) → Service → Repository → SQLAlchemy`

## Key conventions

- **Tables auto-created on startup** via `Base.metadata.create_all()` in lifespan. Alembic installed but not initialized — no migration scripts.
- **Dependency injection** via FastAPI `Depends`. Each module has `deps.py` factories wiring repos into services.
- **Module boilerplate**: create `enums.py` (if needed), `model.py`, `schema.py`, `repository.py`, `service.py`, `router.py`, `deps.py`, then register router in `app/api/v1/api.py`.
- **Product state machine** (`app/modules/products/service.py:_resolve_state`): stock=0 → NO_STOCK, stock>0 + current NO_STOCK → ACTIVE, else leave as-is.
- **Events append-only**: router exposes GET only. Events written inside services via `AuditLogger`.
- **Audit logging** via `app/core/audit.py` `AuditLogger` class. Injected into any service via `Depends(get_audit_logger)`. Methods: `log_create/update/status_change/delete(entity_type, entity_id, user_id, changes)`. All write operations require authenticated user.
- **Env vars**: `DATABASE_URL` (required), `SECRET_KEY` (required for JWT), other vars have defaults. `.env` is gitignored; `.env.example` exists.
- **Pagination**: query params `page` (≥1, default 1) and `size` (1–100, default 20). Return type `PaginatedResponse[T]` with `items`, `total`, `page`, `size`, `pages`.
