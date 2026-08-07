# LogisticSystem API — POS + Inventory

API REST multitenant con autenticación JWT, RBAC (roles/permisos), POS completo (ventas anónimas, pagos, caja registradora, estaciones/mesas, recibos), gestión de productos con imágenes y códigos de barras, estanterías de bodega con validación de capacidad, pedidos con state machine, y auditoría global. FastAPI + SQLAlchemy 2.0 async + PostgreSQL + Alembic.

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
│   ├── permissions.py        # PermissionCode enum ({modulo}_{accion}, 65 permissions)
│   ├── exceptions.py         # AppException + NotFound/Conflict/Forbidden/Unauthorized/BadRequest/Validation
│   ├── repository.py         # BaseRepository ABC (lazy tenant_id del ContextVar)
│   ├── seed.py               # Permisos globales + admin default + seed_tenant_roles()
│   ├── tenant.py             # ContextVar current_tenant_id + resolve_tenant()
│   ├── email.py              # Envío de emails (Resend/SMTP)
│   ├── templates.py          # Templates Jinja2 (emails + render from string + SandboxedEnvironment)
│   ├── pdf.py                # PDFRenderer ABC + Gotenberg + WeasyPrint + Custom (semáforo de concurrencia)
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
    ├── users/                # Auth + profile + image + admin CRUD + PIN login (tenant_id nullable)
    ├── roles/                # CRUD roles por tenant, permisos globales, asignaciones
    ├── shelves/              # CRUD estanterías + items + validación capacidad
    ├── categories/           # CRUD categorías por tenant + asignación a productos
    ├── sales/                # Crear ventas + cancelación + recibo + descuento de stock producto + estantería
    ├── orders/               # Pedidos con state machine + edición pre-DELIVERED + entrega crea venta
    ├── payments/             # Registro de pagos (cash/card/transfer/wallet) + split payments
    ├── payments/             # Registro de pagos (cash/card/transfer/wallet) + split payments
    ├── cash_register/        # Caja registradora: open/close, conteo, desfase, N cajas simultáneas
    ├── stations/             # Puntos de servicio genéricos: mesas/bar/hotel/delivery/mostrador
    ├── tenant_config/        # Config de módulos habilitados por tenant
    ├── api_keys/             # API Keys para integraciones externas
    └── invoice_templates/    # Plantillas HTML de factura por tenant + renderizado + PDF
```

## Multitenant

Schema compartido (misma DB). Cada tenant es una empresa independiente. Aislamiento vía columna `tenant_id` + `ContextVar`.

| Concepto | Detalle |
|----------|---------|
| **Tablas con `tenant_id`** | users (nullable), products, categories, shelves, sales, orders, events (nullable), roles, tenant_configs (UNIQUE), api_keys, invoice_templates (UNIQUE) |
| **Sin `tenant_id`** | shelf_items, sale_items, order_items, product_categories, role_permissions, user_roles (scoped via FK padre), permissions (global) |
| **Unique constraints** | Compuestos `(tenant_id, campo)` para barcode, shelf code, category name, role name |
| **Platform admin** | `is_super_admin=True`, `tenant_id=NULL`. Sin `X-Tenant` header → ve todo. Con `X-Tenant: <slug>` → switchea a ese tenant |
| **Tenant user** | `tenant_id=X`. JWT incluye `tid`. Scoping automático, no necesita header |
| **Tenant context** | `current_tenant_id: ContextVar` → `BaseRepository` lo lee lazy → `Base.get_all/get_id` filtran WHERE |
| **Tenant disable** | `get_current_user` y `resolve_tenant` verifican `Tenant.is_active`. Si `false` → 403 "Este tenant está deshabilitado". Aplica a JWT, API Keys y X-Tenant. |
| **ID fiscal** | `Tenant.business_id` (String 50, nullable) acepta NIT/RUT/ID con caracteres especiales |

### Crear tenant

`POST /tenants` (solo platform admin):
1. Crea registro en `tenants` (name, slug, business_id opcional)
2. `seed_tenant_roles()` crea roles Admin/Operator/Viewer para ese tenant
3. Si se envían `admin_email` + `admin_password` → crea usuario admin con `tenant_id` y rol Admin
4. `_ensure_tenant_config()` crea TenantConfig con todos los módulos habilitados

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
| `POST` | `/api/v1/auth/pin-login` | No | Login rápido con PIN (cajeros) |
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
| `GET` | `/api/v1/tenants/` | `tenants_view` | Listar tenants (paginado + filtros) |
| `POST` | `/api/v1/tenants/` | `tenants_create` | Crear tenant + roles + admin opcional |
| `GET` | `/api/v1/tenants/{id}` | `tenants_view` | Obtener tenant |
| `PUT` | `/api/v1/tenants/{id}` | `tenants_edit` | Actualizar tenant |
| `DELETE` | `/api/v1/tenants/{id}` | `tenants_delete` | Desactivar tenant (soft delete) |

### Productos

| Método | Ruta | Permiso | Descripción |
|--------|------|---------|-------------|
| `GET` | `/api/v1/products/` | `products_view` | Listar (paginado + filtros) |
| `GET` | `/api/v1/products/by-barcode/{barcode}` | `products_view` | Lookup rápido por código de barras (POS) |
| `GET` | `/api/v1/products/{id}` | `products_view` | Obtener |
| `POST` | `/api/v1/products/` | `products_create` | Crear |
| `PUT` | `/api/v1/products/{id}` | `products_edit` | Actualizar |
| `DELETE` | `/api/v1/products/{id}` | `products_delete` | Eliminar |
| `POST` | `/api/v1/products/{id}/image` | `products_upload_image` | Subir imagen |
| `DELETE` | `/api/v1/products/{id}/image` | `products_upload_image` | Eliminar imagen |
| `GET` | `/api/v1/products/{id}/qr` | `products_view` | Datos QR (JSON) |

### Categorías

| Método | Ruta | Permiso | Descripción |
|--------|------|---------|-------------|
| `GET` | `/api/v1/categories/` | `categories_view` | Listar (paginado + filtros) |
| `POST` | `/api/v1/categories/` | `categories_create` | Crear |
| `PUT` | `/api/v1/categories/{id}` | `categories_edit` | Actualizar |
| `DELETE` | `/api/v1/categories/{id}` | `categories_delete` | Eliminar |

### Estanterías

| Método | Ruta | Permiso | Descripción |
|--------|------|---------|-------------|
| `GET` | `/api/v1/shelves/` | `shelves_view` | Listar (paginado + filtros) |
| `GET` | `/api/v1/shelves/{id}` | `shelves_view` | Detalle + items + peso/volumen actual |
| `POST` | `/api/v1/shelves/` | `shelves_create` | Crear |
| `PUT` | `/api/v1/shelves/{id}` | `shelves_edit` | Actualizar |
| `DELETE` | `/api/v1/shelves/{id}` | `shelves_delete` | Eliminar (debe estar vacía) |
| `POST` | `/api/v1/shelves/{id}/items` | `shelves_assign_products` | Asignar producto (upsert) |
| `PUT` | `/api/v1/shelves/{id}/items/{item_id}` | `shelves_assign_products` | Cambiar cantidad |
| `DELETE` | `/api/v1/shelves/{id}/items/{item_id}` | `shelves_assign_products` | Desasignar producto |

### Ventas

| Método | Ruta | Permiso | Descripción |
|--------|------|---------|-------------|
| `GET` | `/api/v1/sales/` | `sales_view` | Listar (paginado + filtros) |
| `GET` | `/api/v1/sales/{id}` | `sales_view` | Detalle + items |
| `POST` | `/api/v1/sales/` | `sales_create` | Crear venta (descuenta stock, customer opcional) |
| `POST` | `/api/v1/sales/{id}/cancel` | `sales_cancel` | Cancelar venta (restaura stock) |
| `GET` | `/api/v1/sales/{id}/receipt` | `sales_view` | Recibo JSON (items, taxes, pagos) |
| `GET` | `/api/v1/sales/{id}/invoice/html` | `sales_view_invoice` | Factura HTML renderizada con plantilla del tenant |
| `GET` | `/api/v1/sales/{id}/invoice/pdf` | `sales_view_invoice` | Factura PDF con caché (servicio externo configurable) |

### Pedidos

| Método | Ruta | Permiso | Descripción |
|--------|------|---------|-------------|
| `GET` | `/api/v1/orders/` | `orders_view` | Listar (paginado + filtros) |
| `GET` | `/api/v1/orders/{id}` | `orders_view` | Detalle + items |
| `POST` | `/api/v1/orders/` | `orders_create` | Crear pedido (valida stock) |
| `PUT` | `/api/v1/orders/{id}` | `orders_edit` | Editar pedido (solo antes de DELIVERED, partial update) |
| `POST` | `/api/v1/orders/{id}/prepare` | `orders_change_state` | CREATED → PREPARING |
| `POST` | `/api/v1/orders/{id}/ready` | `orders_change_state` | PREPARING → READY |
| `POST` | `/api/v1/orders/{id}/deliver` | `orders_change_state` | READY → DELIVERED (crea venta) |

### Pagos

| Método | Ruta | Permiso | Descripción |
|--------|------|---------|-------------|
| `GET` | `/api/v1/payments/` | `payments_view` | Listar pagos |
| `POST` | `/api/v1/payments/` | `payments_create` | Registrar pago (cash/card/transfer/wallet) |
| `GET` | `/api/v1/payments/by-sale/{id}` | `payments_view` | Pagos de una venta |

### Caja Registradora

| Método | Ruta | Permiso | Descripción |
|--------|------|---------|-------------|
| `GET` | `/api/v1/cash-register/` | `cash_register_view` | Caja abierta del usuario actual |
| `POST` | `/api/v1/cash-register/open` | `cash_register_open_close` | Abrir sesión de caja (selecciona caja física por ID) |
| `POST` | `/api/v1/cash-register/close` | `cash_register_open_close` | Cerrar sesión del usuario (conteo + desfase) |
| `GET` | `/api/v1/cash-register/history` | `cash_register_view` | Historial de sesiones de caja |
| `GET` | `/api/v1/cash-registers/` | `cash_register_view` | Listar cajas físicas del tenant |
| `POST` | `/api/v1/cash-registers/` | `cash_register_manage_registers` | Crear caja física |
| `PUT` | `/api/v1/cash-registers/{id}` | `cash_register_manage_registers` | Editar caja física |
| `DELETE` | `/api/v1/cash-registers/{id}` | `cash_register_manage_registers` | Desactivar caja física (soft delete) |

**Regla de negocio**: las cajas físicas se definen una vez (POST /cash-registers/) y permanecen. Al abrir, el cajero selecciona cuál usar (cash_register_id). Una caja física solo puede estar en uso por un usuario a la vez. Si el módulo cash_register está habilitado en TenantConfig, cerrar estación, entregar pedido y crear venta exigen caja abierta. Abrir estación y crear pedido NO requieren caja.

### Estaciones (mesas/bar/hotel/delivery)

| Método | Ruta | Permiso | Descripción |
|--------|------|---------|-------------|
| `GET` | `/api/v1/stations/` | `stations_view` | Listar estaciones |
| `POST` | `/api/v1/stations/` | `stations_create` | Crear estación |
| `GET` | `/api/v1/stations/{id}` | `stations_view` | Detalle + sesión activa |
| `PUT` | `/api/v1/stations/{id}` | `stations_edit` | Editar estación |
| `DELETE` | `/api/v1/stations/{id}` | `stations_delete` | Eliminar estación |
| `POST` | `/api/v1/stations/{id}/open` | `stations_open_close` | Abrir sesión (cliente opcional) |
| `POST` | `/api/v1/stations/{id}/close` | `stations_open_close` | Cerrar y cobrar (crea Sale) |
| `POST` | `/api/v1/stations/{id}/cancel` | `stations_open_close` | Cancelar sesión sin cobrar |
| `GET` | `/api/v1/stations/{id}/items` | `stations_view` | Items de sesión activa |
| `POST` | `/api/v1/stations/{id}/items` | `stations_manage_items` | Agregar items al carrito |
| `PUT` | `/api/v1/stations/{id}/items/{item_id}` | `stations_manage_items` | Modificar cantidad/notas |
| `DELETE` | `/api/v1/stations/{id}/items/{item_id}` | `stations_manage_items` | Cancelar item |
| `POST` | `/api/v1/stations/{id}/items/{item_id}/prepare` | `stations_manage_items` | CREATED→PREPARING |
| `POST` | `/api/v1/stations/{id}/items/{item_id}/ready` | `stations_manage_items` | PREPARING→READY |
| `POST` | `/api/v1/stations/{id}/items/{item_id}/deliver` | `stations_manage_items` | READY→DELIVERED |
| `POST` | `/api/v1/stations/{id}/transfer/{target}` | `stations_open_close` | Mover sesión a otra estación |

### API Keys

| Método | Ruta | Permiso | Descripción |
|--------|------|---------|-------------|
| `GET` | `/api/v1/api-keys/` | `api_keys_view` | Listar API Keys del tenant (paginado + filtros) |
| `POST` | `/api/v1/api-keys/` | `api_keys_create` | Crear API Key (retorna raw_key una sola vez) |
| `GET` | `/api/v1/api-keys/{id}` | `api_keys_view` | Ver API Key |
| `PUT` | `/api/v1/api-keys/{id}` | `api_keys_edit` | Editar nombre/permisos/activo |
| `DELETE` | `/api/v1/api-keys/{id}` | `api_keys_delete` | Eliminar API Key |

**Autenticación**: header `X-Api-Key: <raw_key>` como alternativa a `Authorization: Bearer <JWT>`. Las API Keys tienen permisos propios (subconjunto de PermissionCode). Se hashean con SHA-256.

### Tenant Config

| Método | Ruta | Permiso | Descripción |
|--------|------|---------|-------------|
| `GET` | `/api/v1/tenant-config/{tenant_id}` | `tenant_config_view` | Ver módulos habilitados del tenant |
| `PUT` | `/api/v1/tenant-config/{tenant_id}` | `tenant_config_edit` | Actualizar módulos habilitados |

Módulos disponibles: `products`, `shelves`, `categories`, `sales`, `orders`, `stations`, `cash_register`, `taxes`, `customers`, `payments`.

### Invoice Templates (plantillas de factura)

Plantillas HTML editables por tenant para facturas. Una plantilla por tenant, lazy-create con template default. Renderizado con Jinja2 SandboxedEnvironment (seguro, bloquea `__import__`/`eval`). PDF vía servicio externo configurable (Gotenberg, WeasyPrint, Custom).

| Método | Ruta | Permiso | Descripción |
|--------|------|---------|-------------|
| `GET` | `/api/v1/invoice-templates/` | `invoice_templates_view` | HTML actual del tenant |
| `PUT` | `/api/v1/invoice-templates/` | `invoice_templates_edit` | Guardar HTML editado (valida sintaxis Jinja2) |
| `GET` | `/api/v1/invoice-templates/variables` | `invoice_templates_view` | Lista de `{{ variables }}` disponibles |
| `POST` | `/api/v1/invoice-templates/preview` | `invoice_templates_view` | Renderizar con datos dummy o reales |

**Template variables:** `tenant_name`, `tenant_slug`, `tenant_business_id`, `tenant_logo_url`, `invoice_number`, `invoice_date`, `invoice_date_short`, `status`, `payment_status`, `notes`, `customer_name`, `customer_document`, `customer_email`, `customer_phone`, `customer_address`, `items` (loop `{% for item in items %}`), `payments` (loop `{% for payment in payments %}`), `subtotal`, `tax_total`, `total`, `auto_print`.

**PDF rendering** (`app/core/pdf.py`): `PDFRenderer` ABC con 3 backends — `WeasyPrintRenderer` (local), `GotenbergRenderer` (POST `/forms/chromium/convert/html`), `CustomPDFRenderer` (POST genérico). Semáforo `PDF_CONCURRENCY_LIMIT` (default 5) evita saturar el servicio externo. PDFs guardados en `STORAGE_PATH/invoices/{tenant_id}/factura_{sale_id}.pdf`. `Sale.invoice_pdf_path` actúa como caché; `?regenerate=1` fuerza regeneración.

### Eventos (auditoría)

| Método | Ruta | Permiso | Descripción |
|--------|------|---------|-------------|
| `GET` | `/api/v1/events/` | `events_view` | Listar (paginado + filtros) |
| `GET` | `/api/v1/events/{id}` | `events_view` | Obtener |
| `GET` | `/api/v1/{entity_type}/{entity_id}/events/` | `events_view` | Eventos de entidad |

### Roles

| Método | Ruta | Permiso | Descripción |
|--------|------|---------|-------------|
| `GET` | `/api/v1/roles/` | `roles_view` | Listar roles |
| `POST` | `/api/v1/roles/` | `roles_create` | Crear rol |
| `PUT` | `/api/v1/roles/{id}` | `roles_edit` | Editar rol |
| `DELETE` | `/api/v1/roles/{id}` | `roles_delete` | Eliminar rol |
| `GET` | `/api/v1/roles/permissions/` | `roles_view` | Listar permisos disponibles |
| `GET` | `/api/v1/roles/{id}/permissions` | `roles_view` | Ver permisos de un rol |
| `POST` | `/api/v1/roles/{id}/permissions` | `roles_assign_permissions` | Asignar permisos a rol |
| `POST` | `/api/v1/roles/assign` | `users_assign_roles` | Asignar rol a usuario |

### Usuarios (admin)

| Método | Ruta | Permiso | Descripción |
|--------|------|---------|-------------|
| `GET` | `/api/v1/users/` | `users_view` | Listar usuarios |
| `GET` | `/api/v1/users/{id}` | `users_view` | Obtener usuario |
| `PUT` | `/api/v1/users/{id}` | `users_edit` | Editar usuario |
| `DELETE` | `/api/v1/users/{id}` | `users_delete` | Eliminar usuario |
| `POST` | `/api/v1/users/{id}/image` | `users_upload_image` | Subir imagen |
| `DELETE` | `/api/v1/users/{id}/image` | `users_upload_image` | Eliminar imagen |
| `GET` | `/api/v1/users/{id}/roles` | `users_view` | Ver roles |
| `POST` | `/api/v1/users/{id}/roles` | `users_assign_roles` | Asignar rol |
| `DELETE` | `/api/v1/users/{id}/roles/{role_id}` | `users_assign_roles` | Quitar rol |
| `PUT` | `/api/v1/users/{id}/pin` | `users_set_pin` | Setear PIN de cajero |

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

**Permisos** definidos en `app/core/permissions.py` (`PermissionCode` enum) con convención `{modulo}_{accion}`. 65 permisos. Acciones base: `view`, `create`, `edit`, `delete`. Acciones especiales: `upload_image`, `assign_products`, `open_close`, `manage_items`, `change_state`, `cancel`, `view_invoice`, `assign_roles`, `set_pin`, `assign_permissions`, `manage_registers`.

**Seed** (`app/seed.json`):
- Permisos globales (idempotente, se crean al primer arranque)
- Roles (Admin/Operator/Viewer/Waiter/Cashier) se crean por tenant al llamar `POST /tenants`
- Platform admin default: `ADMIN_EMAIL`/`ADMIN_PASSWORD` env vars, `is_super_admin=True`, sin `tenant_id`

| Rol | Permisos |
|-----|----------|
| `Admin` | todos los 65 permisos |
| `Operator` | products_view/create/edit, shelves_view/edit/assign_products, categories_view, sales_view/create/cancel, orders_view/create/edit/change_state, stations_view/open_close/manage_items, cash_register_view/open_close, taxes_view, customers_view/create, payments_view/create, users_view, roles_view, api_keys_view, tenant_config_view, invoice_templates_view |
| `Viewer` | solo `_view` de todos los módulos |
| `Waiter` | stations_view/open_close/manage_items, orders_view/create/edit, products_view, customers_view, sales_view |
| `Cashier` | cash_register_view/open_close, stations_view/open_close, sales_view/create/cancel/view_invoice, payments_view/create, orders_view/change_state, products_view, customers_view/create |

**`require_permission(code)`** (`app/core/security.py`):
- `is_super_admin=True` → bypass total
- Query: User → UserRole → Role → RolePermission → Permission
- Sin permiso → 403

**Gate de módulo**: si el usuario no tiene ningún permiso que empiece con el nombre del módulo, el frontend no muestra el módulo.

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
- **Tenant disable**: `get_current_user` y `resolve_tenant` chequean `Tenant.is_active`. Si deshabilitado → 403 "Este tenant está deshabilitado"

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
| `payment_status` | str | PENDING\|PAID\|PARTIALLY_PAID\|REFUNDED |
| `notes` | str\|null | |
| `created_by` | int | FK users |
| `cash_register_id` | int\|null | FK cash_register_sessions (si módulo caja habilitado) |
| `invoice_pdf_path` | str(500)\|null | Caché del PDF de factura |

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
| `cash_register_id` | int\|null | FK cash_register_sessions (si módulo caja habilitado) |

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

### Payment

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | int | PK |
| `sale_id` | int | FK sales CASCADE |
| `method` | enum | CASH\|CARD\|TRANSFER\|WALLET\|OTHER |
| `amount` | float | monto pagado |
| `reference` | str(100)\|null | referencia |

### CashRegisterSession

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | int | PK |
| `tenant_id` | int | FK tenants |
| `cash_register_id` | int | FK cash_registers (caja física seleccionada) |
| `user_id` | int | FK users (cajero). 1 sesión abierta por usuario |
| `opening_amount` | float | monto inicial |
| `closing_amount` | float\|null | monto contado al cierre |
| `expected_cash` | float\|null | opening + Σ cash payments |
| `discrepancy` | float\|null | closing - expected |
| `status` | enum | OPEN\|CLOSED |

### Station

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | int | PK |
| `tenant_id` | int | FK tenants |
| `code` | str(50) | único por tenant |
| `name` | str(100)\|null | "Ventana VIP" |
| `area` | str(50)\|null | "Salón Principal" |
| `capacity` | int | informativo (default 1) |
| `status` | enum | AVAILABLE\|OCCUPIED\|RESERVED\|MAINTENANCE |

### StationSession

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | int | PK |
| `station_id` | int | FK stations |
| `customer_id` | int\|null | FK customers |
| `customer_name` | str(200) | denormalizado |
| `total` | float | calculado al close |
| `status` | enum | OPEN\|CLOSED\|CANCELLED |
| `sale_id` | int\|null | FK sales (seteado al close) |
| `cash_register_id` | int\|null | FK cash_register_sessions (seteado al open) |
| `created_by` | int | FK users |

### StationSessionItem

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | int | PK |
| `session_id` | int | FK sessions |
| `product_id` | int | FK products |
| `quantity` | int | |
| `unit_price` | float | snapshot |
| `subtotal` | float | qty * unit_price |
| `status` | enum | CREATED→PREPARING→READY→DELIVERED\|CANCELLED |
| `notes` | str(500)\|null | |

### Tenant

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | int | PK |
| `name` | str(200) | nombre empresa |
| `slug` | str(100) | único, URL-safe (regex `^[a-z0-9-]+$`) |
| `business_id` | str(50)\|null | NIT/RUT/identificador fiscal |
| `is_active` | bool | default true |
| `logo_path` | str(500)\|null | |
| `created_at` | datetime | |
| `updated_at` | datetime | |

### TenantConfig

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | int | PK |
| `tenant_id` | int | FK tenants, UNIQUE |
| `modules_enabled` | JSON (str[]) | Módulos habilitados. Default todos |
| `created_at` | datetime | |
| `updated_at` | datetime | |

### ApiKey

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | int | PK |
| `tenant_id` | int | FK tenants |
| `name` | str(200) | Nombre descriptivo |
| `key_prefix` | str(12) | Primeros 12 chars de la key (display) |
| `key_hash` | str(255) | SHA-256 de la key (nunca se expone) |
| `permissions` | JSON (str[]) | Lista de PermissionCode |
| `is_active` | bool | default true |
| `expires_at` | datetime\|null | Fecha de expiración |
| `last_used_at` | datetime\|null | Último uso |
| `created_by` | int | FK users |
| `created_at` | datetime | |
| `updated_at` | datetime | |

### InvoiceTemplate

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | int | PK |
| `tenant_id` | int | FK tenants, UNIQUE (una plantilla por tenant) |
| `html_content` | str | HTML completo con placeholders Jinja2 |
| `created_at` | datetime | |
| `updated_at` | datetime | |

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
| `PDF_RENDERER` | `weasyprint` | Backend PDF: `weasyprint`, `gotenberg`, `custom` |
| `PDF_SERVICE_URL` | *(vacío)* | URL del servicio externo PDF (para gotenberg/custom) |
| `PDF_CONCURRENCY_LIMIT` | `5` | Máximo de renders PDF simultáneos |

Sin defaults hardcodeados. Solo `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `RESEND_API_KEY`, `PDF_SERVICE_URL` tienen default vacío (opcionales reales). `PDF_RENDERER` y `PDF_CONCURRENCY_LIMIT` tienen defaults razonables.

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

## Test data

Script `scripts/seed_test_data.py` crea 3 tenants con datos de prueba:

```bash
pip install httpx
python3 scripts/seed_test_data.py [--base-url http://localhost:8000/api/v1]
```

| Tenant | Productos | Estaciones | Estanterías | Cajas | Usuarios |
|--------|-----------|------------|-------------|-------|----------|
| `restaurante-demo` | 20 (5 cat) | 11 (mesas + delivery) | — | 1 | admin, mesero, cajera, viewer |
| `ferreteria-demo` | 100 (8 cat) | — | 6 con 100 items | 2 | admin, vendedor, cajera, viewer |
| `hotel-demo` | 15 (4 cat) | 20 (habitaciones) | — | 4 | admin, recepcionista, 3 cajeros, viewer |

Credenciales: `admin@{slug}.demo` / `admin123` (admin), `oper123` (operator), `view123` (viewer).
