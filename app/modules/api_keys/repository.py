from sqlalchemy import select

from app.core.repository import BaseRepository
from app.modules.api_keys.model import ApiKey


class ApiKeyRepository(BaseRepository):
    model = ApiKey

    async def find_by_hash(self, key_hash: str) -> ApiKey | None:
        result = await self.db.scalar(
            select(ApiKey).where(ApiKey.key_hash == key_hash)
        )
        return result

    async def get_by_tenant(self, tenant_id: int) -> list[ApiKey]:
        result = await self.db.scalars(
            select(ApiKey).where(ApiKey.tenant_id == tenant_id)
        )
        return list(result.all())
