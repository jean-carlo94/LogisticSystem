# LogisticSystem API

API REST para gestión de productos construida con FastAPI, SQLAlchemy y PostgreSQL.

## Estructura del proyecto

```
LogisticSystem/
├── app/
│   ├── main.py                  # Punto de entrada, lifespan, registro de rutas
│   ├── core/
│   │   ├── config.py            # Configuración con pydantic-settings
│   │   └── database.py          # Engine, SessionLocal, Base y get_db
│   ├── modules/
│   │   ├── products/
│   │   │   ├── deps.py          # Factorías de inyección (repo, service)
│   │   │   ├── model.py         # Modelo SQLAlchemy (Product)
│   │   │   ├── repository.py    # Acceso a datos (ProductRepository)
│   │   │   ├── schema.py        # Schemas Pydantic (CRUD + response)
│   │   │   ├── service.py       # Lógica de negocio (ProductService)
│   │   │   └── router.py        # Endpoints REST
│   │   └── events/
│   │       ├── deps.py          # Factorías de inyección (repo, service)
│   │       ├── enums.py         # ActionType enum
│   │       ├── model.py         # Modelo SQLAlchemy (Event)
│   │       ├── repository.py    # Acceso a datos (EventRepository)
│   │       ├── schema.py        # Schema Pydantic (EventResponse)
│   │       ├── service.py       # Lógica de negocio (EventService)
│   │       └── router.py        # Endpoints REST (solo lectura)
│   └── api/v1/
│       └── api.py               # Router principal v1
├── docker-compose.yml
├── Dockerfile
├── start.sh                     # Entrypoint del contenedor
├── wait_for_db.py               # Espera a que PostgreSQL esté listo
├── .env                         # Variables de entorno
└── requirements.txt
```

## Arquitectura

El proyecto sigue una arquitectura en capas con inyección de dependencias:

```
Router ──Depends──> Service ──Depends──> Repository ──> SQLAlchemy
```

| Capa | Responsabilidad |
|------|----------------|
| `router.py` | Endpoints HTTP, validación de entrada/salida |
| `service.py` | Lógica de negocio, orquestación |
| `repository.py` | Acceso a datos, queries SQLAlchemy |
| `model.py` | Definición de tablas (ORM) |
| `schema.py` | Schemas Pydantic (DTOs) |
| `deps.py` | Factorías de inyección con `Depends` |

Cada petición recorre la cadena: el router recibe el servicio ya construido con sus repositorios inyectados.

## Requisitos

- [Docker](https://docs.docker.com/get-docker/) y Docker Compose
- O alternativamente: Python 3.12+ y PostgreSQL

## Endpoints

### Productos

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/v1/products/` | Listar productos |
| `GET` | `/api/v1/products/{id}` | Obtener producto |
| `POST` | `/api/v1/products/` | Crear producto |
| `PUT` | `/api/v1/products/{id}` | Actualizar producto |
| `DELETE` | `/api/v1/products/{id}` | Eliminar producto |

### Eventos (solo lectura)

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/v1/events/` | Listar todos los eventos |
| `GET` | `/api/v1/events/{id}` | Obtener un evento |
| `GET` | `/api/v1/products/{id}/events/` | Eventos de un producto |

### Sistema

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/` | Mensaje de bienvenida |
| `GET` | `/health` | Health check |

**Documentación interactiva:**  
- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)  
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Modelo Product

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | `int` | Identificador único (autoincremental) |
| `name` | `string` | Nombre del producto (requerido, máx 200) |
| `description` | `string \| null` | Descripción del producto |
| `price` | `float` | Precio (requerido, > 0) |
| `stock` | `int` | Cantidad en inventario (default 0) |
| `state` | `string` | Estado del producto (default "active") |
| `create_at` | `datetime` | Fecha de creación (automática) |

## Modelo Event

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | `int` | Identificador único (autoincremental) |
| `product_id` | `int` | ID del producto relacionado |
| `action` | `enum` | `CREATE`, `UPDATE`, `DELETE`, `STATUS_CHANGED` |
| `description` | `string \| null` | JSON con el DTO o datos de la acción |
| `create_at` | `datetime` | Fecha de creación (automática) |

> Los eventos se registran automáticamente al crear, actualizar o eliminar productos.  
> La descripción es un JSON del DTO: en `CREATE` lleva todos los campos, en `UPDATE` solo los modificados, y en `STATUS_CHANGED` el estado anterior y nuevo.

## Instalación y ejecución

### Opción 1: Docker Compose (recomendado)

```bash
# 1. Clonar el repositorio
git clone <repo-url>
cd LogisticSystem

# 2. (Opcional) Editar variables de entorno
# El archivo .env ya contiene valores por defecto funcionales.
nano .env

# 3. Construir y levantar los servicios
docker compose up --build -d

# 4. Verificar que todo esté funcionando
curl http://localhost:8000/health
# Respuesta esperada: {"status":"healthy"}

# 5. Probar la API
curl -X POST http://localhost:8000/api/v1/products/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Laptop", "price": 999.99, "stock": 10}'

curl http://localhost:8000/api/v1/products/

# 6. Detener los servicios
docker compose down
```

### Opción 2: Desarrollo local (sin Docker)

```bash
# 1. Clonar y crear entorno virtual
git clone <repo-url>
cd LogisticSystem
python3 -m venv venv
source venv/bin/activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar la base de datos
# Define DATABASE_URL en .env apuntando a tu PostgreSQL:
#   DATABASE_URL=postgresql://usuario:password@localhost:5432/nombre_db

# 4. Ejecutar la aplicación
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# La API estará disponible en http://localhost:8000
```

## Variables de entorno (.env)

| Variable | Valor por defecto | Descripción |
|----------|-------------------|-------------|
| `DATABASE_URL` | *(requerido)* | URL de conexión a la BD |
| `POSTGRES_USER` | `asisprex_user` | Usuario de PostgreSQL |
| `POSTGRES_PASSWORD` | `asisprex_pass` | Contraseña de PostgreSQL |
| `POSTGRES_DB` | `asisprex_db` | Nombre de la base de datos |
| `SECRET_KEY` | `dev-secret-key...` | Clave secreta de la app |
| `API_V1_STR` | `/api/v1` | Prefijo de la API |
| `PROJECT_NAME` | `LogisticSystem API` | Nombre del proyecto |
| `APP_PORT` | `8000` | Puerto de la aplicación |

> Al usar Docker Compose, `DATABASE_URL` se inyecta automáticamente apuntando al contenedor de PostgreSQL.  
> En desarrollo local debe definirse explícitamente en `.env`.
