# AGENTS.md - LogisticSystem API

## Commands

```bash
# Dev (local, needs PostgreSQL)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Docker (standalone, preferred)
docker compose up --build -d
docker compose down
```

No test suite, linter, formatter, or typechecker is configured. The `.gitignore` excludes `venv/` and `.env`.

## Architecture

```
app/
├── main.py              # FastAPI app, lifespan (creates tables), CORS, root/health routes
├── core/
│   ├── config.py        # pydantic-settings from .env
│   ├── database.py      # engine, sessionmaker, Base, get_db generator
│   └── pagination.py    # PaginatedResult + PaginatedResponse (page/size query params)
├── api/v1/api.py        # Aggregates products + events routers under /api/v1 prefix
└── modules/
    ├── products/        # CRUD + state enforcement → ProductState enum
    └── events/          # Read-only audit log → ActionType enum
```

Layer chain: `router → Depends(deps.py factory) → Service → Repository → SQLAlchemy`

## Key conventions

- **Tables auto-created on startup** via `Base.metadata.create_all()` in the lifespan handler. Alembic is installed but not initialized — there are no migration scripts.
- **Dependency injection** via FastAPI `Depends`. Each module has `deps.py` factories that wire repos into services.
- **Module boilerplate**: adding a new module means creating `enums.py` (if needed), `model.py`, `schema.py`, `repository.py`, `service.py`, `router.py`, `deps.py`, then registering the router in `app/api/v1/api.py`.
- **Product state machine** (`app/modules/products/service.py:_resolve_state`): stock=0 → NO_STOCK, stock>0 + current state is NO_STOCK → ACTIVE, otherwise leave as-is.
- **Events are append-only**: the event router exposes GET endpoints only. Events are written inside `ProductService.create/update/delete`.
- **Env vars**: `DATABASE_URL` (required), other vars have defaults. `.env` is gitignored; `.env.example` exists.
- **Pagination**: query params `page` (≥1, default 1) and `size` (1–100, default 20). Return type is `PaginatedResponse[T]` which has `items`, `total`, `page`, `size`, `pages`.
