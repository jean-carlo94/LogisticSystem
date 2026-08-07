import secrets

from app.core.audit import AuditLogger
from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.core.pagination import PaginatedResponse
from app.core.security import hash_api_key
from app.core.tenant import current_tenant_id
from app.modules.api_keys.model import ApiKey
from app.modules.api_keys.repository import ApiKeyRepository
from app.modules.api_keys.schema import (
    ApiKeyCreate, ApiKeyCreatedResponse, ApiKeyUpdate, ApiKeyResponse,
)


class ApiKeyService:
    def __init__(self, repo: ApiKeyRepository, audit: AuditLogger):
        self.repo = repo
        self.audit = audit

    async def get_all(
        self, page: int = 1, size: int = 20, filters: dict | None = None
    ) -> PaginatedResponse:
        skip = (page - 1) * size
        items, total = await self.repo.get_all(
            skip=skip, limit=size, filters=filters
        )
        return PaginatedResponse.of(list(items), total, page, size)

    async def create(
        self, data: ApiKeyCreate, user_id: int
    ) -> ApiKeyCreatedResponse:
        tid = current_tenant_id.get()
        if tid is None:
            raise ValidationException("Debe especificar un tenant (use header X-Tenant)")

        raw_key = f"ak_{secrets.token_hex(24)}"
        key_prefix = raw_key[:12]
        key_hash = hash_api_key(raw_key)

        pk = await self.repo.create(
            tenant_id=tid,
            name=data.name,
            key_prefix=key_prefix,
            key_hash=key_hash,
            permissions=data.permissions,
            expires_at=data.expires_at,
            created_by=user_id,
        )
        await self.audit.log_create("ApiKey", pk.id, user_id, pk)

        return ApiKeyCreatedResponse(
            id=pk.id,
            tenant_id=pk.tenant_id,
            name=pk.name,
            key_prefix=pk.key_prefix,
            permissions=pk.permissions,
            is_active=pk.is_active,
            expires_at=pk.expires_at,
            last_used_at=pk.last_used_at,
            created_by=pk.created_by,
            created_at=pk.created_at,
            updated_at=pk.updated_at,
            raw_key=raw_key,
        )

    async def get_by_id(self, key_id: int) -> ApiKeyResponse:
        key = await self.repo.get_by_id(key_id)
        if not key:
            raise NotFoundException("API Key no encontrada")
        return key

    async def update(
        self, key_id: int, data: ApiKeyUpdate, user_id: int
    ) -> ApiKeyResponse:
        key = await self.repo.get_by_id(key_id)
        if not key:
            raise NotFoundException("API Key no encontrada")

        update_data = data.model_dump(exclude_unset=True)
        await self.repo.update(key, **update_data)
        await self.audit.log_update("ApiKey", key.id, user_id, update_data)
        return key

    async def delete(self, key_id: int, user_id: int) -> None:
        key = await self.repo.get_by_id(key_id)
        if not key:
            raise NotFoundException("API Key no encontrada")
        await self.audit.log_delete("ApiKey", key.id, user_id, key)
        await self.repo.delete(key)
