# Frontend API — Autenticacion, Activacion y Recuperacion

Base URL: `http://localhost:8000/api/v1`

---

## POST /auth/register

Registra nuevo usuario. El usuario se crea **inactivo** (`is_active: false`) y se envia email de activacion.

**Body** (JSON):

```json
{
  "email": "user@example.com",
  "password": "secreto123",
  "first_name": "Juan",
  "last_name": "Perez",
  "phone": "+56912345678",
  "city": "Santiago",
  "country": "Chile"
}
```

| Campo | Tipo | Requerido | Validacion |
|-------|------|-----------|------------|
| email | string (email) | SI | formato email valido |
| password | string | SI | 6-128 caracteres |
| first_name | string \| null | NO | max 100 |
| last_name | string \| null | NO | max 100 |
| phone | string \| null | NO | max 30 |
| city | string \| null | NO | max 100 |
| country | string \| null | NO | max 100 |

**Respuesta**: `201 Created`

```json
{
  "id": 2,
  "email": "user@example.com",
  "first_name": "Juan",
  "last_name": "Perez",
  "phone": null,
  "city": null,
  "country": null,
  "is_active": false,
  "image_path": null,
  "image_url": null,
  "created_at": "2026-07-27T22:02:37.735202",
  "updated_at": "2026-07-27T22:02:37.735202"
}
```

**Errores**:

| Status | Body | Causa |
|--------|------|-------|
| 409 | `{"detail":"El email ya esta registrado"}` | Email duplicado |
| 422 | `{"detail":[{"loc":["body","email"],"msg":"value is not a valid email"}]}` | Validacion |
| 500 | `{"detail":"No se pudo enviar el email de activacion. Por favor intenta de nuevo."}` | Fallo envio email |

**Flujo frontend**:
1. Usuario llena formulario y envia `POST /auth/register`
2. Si 201 → mostrar "Revisa tu correo para activar tu cuenta"
3. Si 500 → mostrar "Error al enviar email. Intenta de nuevo."
4. Si 409 → email ya registrado

---

## POST /auth/login

Inicia sesion. **Usuario inactivo no puede loguearse** — debe activar cuenta primero.

**Body** (JSON):

```json
{
  "email": "user@example.com",
  "password": "secreto123"
}
```

| Campo | Tipo | Requerido |
|-------|------|-----------|
| email | string (email) | SI |
| password | string | SI |

**Respuesta**: `200 OK`

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

El `access_token` se envia como header en peticiones autenticadas:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

**Errores**:

| Status | Body | Causa |
|--------|------|-------|
| 401 | `{"detail":"Email o contrasena incorrectos"}` | Credenciales invalidas |
| 401 | `{"detail":"Sesion invalida. La contrasena fue cambiada. Inicia sesion de nuevo."}` | Se cambio password, JWT invalido |
| 403 | `{"detail":"Cuenta no activada. Revisa tu correo para activarla."}` | Usuario no activo |

---

## POST /auth/activate

Activa la cuenta del usuario con el token recibido por email. **Rate limit: 10 req/min por IP**.

**Body** (JSON):

```json
{
  "token": "aGVsbG8gd29ybGQ..."
}
```

| Campo | Tipo | Requerido | Validacion |
|-------|------|-----------|------------|
| token | string | SI | min 1, max 256 caracteres |

**Respuesta**: `200 OK`

```json
{
  "message": "Cuenta activada correctamente"
}
```

**Errores**:

| Status | Body | Causa |
|--------|------|-------|
| 400 | `{"detail":"Token invalido o expirado"}` | Token no existe, ya usado o expiro |
| 400 | `{"detail":"La cuenta ya esta activada"}` | Ya fue activada antes |
| 429 | `{"detail":"Demasiadas solicitudes. Intenta de nuevo mas tarde."}` | Rate limit excedido |

**Flujo frontend**:
1. Usuario hace click en link del email: `{FRONTEND_URL}/verify-email?token=xxx`
2. Pagina `/verify-email` captura `token` del query string
3. Llama `POST /api/v1/auth/activate` con body `{"token": "<token>"}`
4. Si 200 → mostrar "Cuenta activada", redirigir a login
5. Si 400 → mostrar mensaje de error + boton "Reenviar email de activacion"
6. Si 429 → mostrar "Demasiados intentos, espera un minuto"

---

## POST /auth/resend-activation

Reenvia el email de activacion. **Siempre retorna 200** (anti-enumeracion). Solo envia si el email existe y la cuenta no esta activada.

**Body** (JSON):

```json
{
  "email": "user@example.com"
}
```

| Campo | Tipo | Requerido |
|-------|------|-----------|
| email | string (email) | SI |

**Respuesta**: `200 OK`

```json
{
  "message": "Si el email existe y la cuenta no esta activada, recibiras un nuevo correo"
}
```

**Flujo frontend**:
1. Usuario en pagina `/verify-email` pulsa "Reenviar email"
2. Llama `POST /auth/resend-activation` con `{"email": "..."}` (puede venir del estado de registro o de un campo input)
3. Mostrar "Si tu cuenta existe, recibiras un nuevo email"
4. Si falla el envio (500), mostrar error

---

## POST /auth/forgot-password

Solicita recuperacion de contraseña. Envia email con link de reset. **Rate limit: 5 req/min por IP**. **Usuarios inactivos no reciben email** (silenciado por anti-enumeracion).

**Body** (JSON):

```json
{
  "email": "user@example.com"
}
```

| Campo | Tipo | Requerido |
|-------|------|-----------|
| email | string (email) | SI |

**Respuesta**: `200 OK`

```json
{
  "message": "Si el email existe, recibiras instrucciones para restablecer tu contrasena"
}
```

**Errores**:

| Status | Body | Causa |
|--------|------|-------|
| 429 | `{"detail":"Demasiadas solicitudes. Intenta de nuevo mas tarde."}` | Rate limit excedido |

**Flujo frontend**:
1. Usuario ingresa email en formulario
2. Frontend llama `POST /auth/forgot-password`
3. Si 200 → mostrar mensaje de exito (no revelar si el email existe)
4. Si 429 → mostrar "Demasiados intentos, espera un minuto"
5. Usuario revisa su correo — link: `{FRONTEND_URL}/reset-password?token=xxx`

---

## POST /auth/reset-password

Restablece la contraseña usando el token del email. **Invalida todos los JWTs anteriores** del usuario (si alguien tenia sesion abierta, la pierde). Si el usuario estaba inactivo, **lo activa automaticamente**.

**Body** (JSON):

```json
{
  "token": "aGVsbG8gd29ybGQ...",
  "new_password": "nuevaclave123"
}
```

| Campo | Tipo | Requerido | Validacion |
|-------|------|-----------|------------|
| token | string | SI | min 1, max 256 caracteres |
| new_password | string | SI | 6-128 caracteres |

**Respuesta**: `200 OK`

```json
{
  "message": "Contrasena actualizada correctamente"
}
```

**Errores**:

| Status | Body | Causa |
|--------|------|-------|
| 400 | `{"detail":"Token invalido o expirado"}` | Token no existe, ya usado o expiro |

**Flujo frontend**:
1. Usuario hace click en link del email: `{FRONTEND_URL}/reset-password?token=xxx`
2. Pagina `/reset-password` captura `token` del query string
3. Mostrar formulario: campo `new_password` + confirmacion
4. Validar que ambas contraseñas coincidan y cumplan min 6 caracteres
5. Llamar `POST /api/v1/auth/reset-password` con `{"token": "...", "new_password": "..."}`
6. Si 200 → mostrar "Contraseña actualizada. Inicia sesion."
7. Si 400 → mostrar "Link invalido o expirado", ofrecer solicitar otro

---

## GET /auth/me

Obtiene el perfil del usuario autenticado (roles y permisos incluidos).

**Headers**:
```
Authorization: Bearer <access_token>
```

**Respuesta**: `200 OK`

```json
{
  "id": 1,
  "email": "admin@logistics.com",
  "first_name": "Admin",
  "last_name": null,
  "phone": null,
  "city": null,
  "country": null,
  "is_active": true,
  "is_super_admin": true,
  "image_path": null,
  "image_url": null,
  "created_at": "2026-07-27T21:34:22.088844",
  "updated_at": "2026-07-27T21:34:22.088844",
  "roles": [
    {"id": 1, "name": "Admin"}
  ],
  "permissions": [
    "products_create",
    "products_read",
    "products_update",
    ...
  ]
}
```

**Errores**:

| Status | Body | Causa |
|--------|------|-------|
| 401 | `{"detail":"Credenciales invalidas o expiradas"}` | Token ausente o expirado |
| 401 | `{"detail":"Sesion invalida. La contrasena fue cambiada. Inicia sesion de nuevo."}` | Cambio de password invalido el JWT |

---

## PUT /auth/me

Actualiza perfil propio. Todos los campos son opcionales.

**Headers**: `Authorization: Bearer <access_token>`

**Body** (JSON):

```json
{
  "first_name": "Juan",
  "last_name": "Perez",
  "phone": "+56912345678",
  "city": "Santiago",
  "country": "Chile",
  "password": "nuevaclave123"
}
```

| Campo | Tipo | Requerido | Validacion |
|-------|------|-----------|------------|
| first_name | string \| null | NO | |
| last_name | string \| null | NO | |
| phone | string \| null | NO | |
| city | string \| null | NO | |
| country | string \| null | NO | |
| password | string \| null | NO | 6-128 caracteres |

**Respuesta**: `200 OK` → `UserResponse` (mismos campos que register)

---

## POST /auth/me/image

Sube avatar/imagen de perfil.

**Headers**: `Authorization: Bearer <access_token>`
**Content-Type**: `multipart/form-data`

| Campo | Tipo | Requerido |
|-------|------|-----------|
| file | file | SI |

**Respuesta**: `200 OK` → `UserResponse` con `image_path` y `image_url` poblados.

---

## DELETE /auth/me/image

Elimina el avatar.

**Headers**: `Authorization: Bearer <access_token>`

**Respuesta**: `204 No Content`

---

## Paginas frontend necesarias

| Ruta | Funcion |
|------|---------|
| `/login` | Formulario email + password → `POST /auth/login` |
| `/register` | Formulario registro → `POST /auth/register` → mostrar "Revisa tu correo" |
| `/verify-email?token=xxx` | Captura token del query string → `POST /auth/activate` con body `{token}` |
| `/forgot-password` | Formulario email → `POST /auth/forgot-password` |
| `/reset-password?token=xxx` | Formulario nueva contraseña → `POST /auth/reset-password` |
| `/profile` | `GET /auth/me` + formulario edicion → `PUT /auth/me` |

---

## Rate limits

| Endpoint | Limite | Ventana |
|----------|--------|---------|
| `/auth/forgot-password` | 5 req | 60 seg |
| `/auth/activate` | 10 req | 60 seg |
| Global (todos) | 1000 req | 60 seg |

---

## Comportamiento JWT

- Expiracion: 24 horas (`ACCESS_TOKEN_EXPIRE_HOURS`)
- Si el usuario cambia su password (via reset o update de perfil), **todos los JWTs anteriores se invalidan**
- El backend devuelve `401 "Sesion invalida. La contrasena fue cambiada. Inicia sesion de nuevo."` — frontend debe redirigir a `/login`
- Si una peticion autenticada devuelve 401, redirigir a `/login` (redirigir al usuario a login en lugar de mostrar el error crudo)

## Configuracion en .env (backend)

```bash
FRONTEND_URL=http://localhost:5173          # base URL del frontend para links en emails
PASSWORD_RESET_TOKEN_EXPIRE_MINUTES=30      # expiracion token reset (minutos)
ACCOUNT_ACTIVATION_EXPIRE_HOURS=24          # expiracion token activacion (horas)
ACCESS_TOKEN_EXPIRE_HOURS=24                # expiracion JWT (horas)
```

## Notas para el frontend

- El token de acceso expira en 24 horas. Renovar via `POST /auth/login`.
- `POST /auth/forgot-password` y `POST /auth/resend-activation` siempre devuelven 200 — no uses su respuesta para validar si un email existe.
- `POST /auth/activate` usa el token en el body, no como query param.
- Los emails se envian desde el dominio verificado en Resend. Si usas un email de prueba que no sea del dominio verificado, fallara el envio (500 en register).
- Si cambias de password (via reset o perfil), cierra la sesion del usuario y envia a login — el backend rechazara el JWT viejo.
