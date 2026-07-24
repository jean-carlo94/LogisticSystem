# LogisticSystem API

API REST con autenticación JWT, gestión de productos y auditoría global. Construida con FastAPI, SQLAlchemy y PostgreSQL.

## Estructura del proyecto

```
app/
├── main.py                  # Punto de entrada, lifespan (crea tablas), CORS
├── core/
│   ├── config.py            # Configuración con pydantic-settings
│   ├── database.py          # Engine, SessionLocal, Base con CRUD global
│   ├── security.py          # JWT, hash de passwords, get_current_user
│   ├── audit.py             # AuditLogger inyectable (logs globales)
│   └── pagination.py        # PaginatedResult + PaginatedResponse
├── api/v1/
│   └── api.py               # Router principal v1
└── modules/
    ├── products/            # CRUD de productos + máquina de estados
    ├── events/              # Auditoría genérica (entity_type + entity_id + user_id)
    └── users/               # Registro, login, JWT
```

## Arquitectura

```
Router ──Depends──> Service ──Depends──> Repository ──> Base (modelo con CRUD)
```

Cada modelo hereda de `Base` (`app/core/database.py`) y obtiene automáticamente:

| Método | Nivel | Descripción |
|--------|-------|-------------|
| `get_id(db, id)` | classmethod | `db.get(cls, id)` |
| `get_all(db, skip, limit, order_by)` | classmethod | Listado paginado |
| `create(db, **kwargs)` | classmethod | Instancia + `add/commit/refresh` |
| `save(db)` | instancia | Persiste cambios |
| `update(db, **kwargs)` | instancia | `setattr` por campo (dispara setters) |
| `delete(db)` | instancia | Elimina registro |

Los **property setters** de cada modelo se ejecutan automáticamente al usar `create()` y `update()`. No se requiere `__init__` manual.

## Autenticación

JWT con expiración de 24 horas. Endpoints protegidos requieren header `Authorization: Bearer <token>`.

```bash
# Registro
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"usuario@email.com","password":"123456"}'

# Login (devuelve access_token)
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"usuario@email.com","password":"123456"}'
```

## Auditoría Global

Clase `AuditLogger` (`app/core/audit.py`) inyectable en cualquier servicio vía `Depends(get_audit_logger)`:

```python
self.audit.log_create("Product", entity.id, user_id, data)
self.audit.log_update("Product", entity.id, user_id, changes)
self.audit.log_status_change("Product", entity.id, user_id, old, new)
self.audit.log_delete("Product", entity.id, user_id, summary)
```

Tabla `events` — genérica: `entity_type`, `entity_id`, `action`, `user_id`, `description`, `create_at`.

## Endpoints

### Auth

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| `POST` | `/api/v1/auth/register` | No | Registrar usuario |
| `POST` | `/api/v1/auth/login` | No | Iniciar sesión |
| `GET` | `/api/v1/auth/me` | Sí | Datos del usuario autenticado |

### Productos

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| `GET` | `/api/v1/products/` | Sí | Listar productos |
| `GET` | `/api/v1/products/{id}` | Sí | Obtener producto |
| `POST` | `/api/v1/products/` | Sí | Crear producto |
| `PUT` | `/api/v1/products/{id}` | Sí | Actualizar producto |
| `DELETE` | `/api/v1/products/{id}` | Sí | Eliminar producto |

### Eventos (auditoría)

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| `GET` | `/api/v1/events/` | Sí | Listar todos los eventos |
| `GET` | `/api/v1/events/{id}` | Sí | Obtener un evento |
| `GET` | `/api/v1/{entity_type}/{entity_id}/events/` | Sí | Eventos de una entidad |

### Sistema

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| `GET` | `/` | No | Mensaje de bienvenida |
| `GET` | `/health` | No | Health check |

**Documentación interactiva:**  
- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)  
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Modelos

### Product

| Campo | Tipo | Setter |
|-------|------|--------|
| `id` | `int` | — |
| `name` | `string` | `.strip()` |
| `description` | `string \| null` | — |
| `price` | `float` | `round(2)` |
| `stock` | `int` | `max(0, value)` |
| `state` | `enum` | `ACTIVE`, `INACTIVE`, `NO_STOCK`, `DISCONTINUED` |
| `create_at` | `datetime` | automático |

Máquina de estados (`_resolve_state`): stock=0 → `NO_STOCK`, stock>0 + `NO_STOCK` → `ACTIVE`.

### Event

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | `int` | Auto |
| `entity_type` | `string` | Tipo de entidad (`Product`, `User`, ...) |
| `entity_id` | `int` | ID de la entidad |
| `action` | `enum` | `CREATE`, `UPDATE`, `DELETE`, `STATUS_CHANGED` |
| `user_id` | `int` | Usuario que realizó la acción |
| `description` | `string \| null` | JSON con datos del cambio |
| `create_at` | `datetime` | Automático |

### User

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | `int` | Auto |
| `email` | `string` | Único |
| `hashed_password` | `string` | Hash bcrypt |
| `is_active` | `bool` | Default `true` |
| `created_at` | `datetime` | Automático |

## Instalación

### Docker Compose (recomendado)

```bash
git clone <repo-url>
cd LogisticSystemAPI

# Configurar .env
cp .env.example .env
# Editar DATABASE_URL, SECRET_KEY, etc.

docker compose up --build -d
curl http://localhost:8000/health
# {"status":"healthy"}
```

### Desarrollo local

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# .env: DATABASE_URL=postgresql://user:pass@localhost:5432/db
# .env: SECRET_KEY=<clave-segura>

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Variables de entorno

| Variable | Default | Descripción |
|----------|---------|-------------|
| `DATABASE_URL` | *(requerido)* | Conexión PostgreSQL |
| `SECRET_KEY` | *(requerido)* | Clave para firmar JWT |
| `API_V1_STR` | `/api/v1` | Prefijo de rutas |
| `PROJECT_NAME` | `Logistic System API` | Título en docs |
| `ACCESS_TOKEN_EXPIRE_HOURS` | `24` | Expiración del JWT |
| `CORS_ORIGINS` | `["*"]` | Orígenes permitidos |
| `APP_PORT` | `8000` | Puerto HTTP |

## Agregar un nuevo módulo

Crear estructura estándar y heredar de `Base`:

```
app/modules/nuevo/
├── __init__.py
├── enums.py       # (opcional)
├── model.py       # class Nuevo(Base): ...
├── schema.py      # Pydantic DTOs
├── repository.py  # Delega en métodos de Base
├── service.py     # Lógica de negocio
├── router.py      # Endpoints
└── deps.py        # Factorías Depends
```

Registrar router en `app/api/v1/api.py`. Para auditoría inyectar `AuditLogger` vía `Depends(get_audit_logger)`.
