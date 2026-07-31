from __future__ import annotations

from app.core.audit import AuditLogger
from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.core.pagination import PaginatedResponse
from app.core.tenant import current_tenant_id
from app.modules.taxes.model import Tax
from app.modules.taxes.repository import TaxRepository
from app.modules.taxes.schema import TaxCreate, TaxUpdate


class TaxService:
    def __init__(self, repo: TaxRepository, audit: AuditLogger):
        self.repo = repo
        self.audit = audit

    async def get_all(
        self, page: int = 1, size: int = 20, filters: dict | None = None
    ) -> PaginatedResponse[Tax]:
        skip = (page - 1) * size
        items, total = await self.repo.get_all(skip=skip, limit=size, filters=filters)
        return PaginatedResponse.of(list(items), total, page, size)

    async def create(self, data: TaxCreate, user_id: int) -> Tax:
        if current_tenant_id.get() is None:
            raise ValidationException("Debe especificar un tenant (use header X-Tenant)")
        if await self.repo.find_by_name(data.name):
            raise ConflictException("El impuesto ya existe")
        tax = await self.repo.create(**data.model_dump())
        await self.audit.log_create("Tax", tax.id, user_id, tax)
        return tax

    async def update(self, tax_id: int, data: TaxUpdate, user_id: int) -> Tax:
        tax = await self.repo.get_by_id(tax_id)
        if not tax:
            raise NotFoundException("Impuesto no encontrado")
        update_data = data.model_dump(exclude_unset=True)
        if "name" in update_data:
            existing = await self.repo.find_by_name(update_data["name"])
            if existing and existing.id != tax_id:
                raise ConflictException("El nombre ya esta en uso")
        await self.repo.update(tax, **update_data)
        await self.audit.log_update("Tax", tax.id, user_id, update_data)
        return tax

    async def delete(self, tax_id: int, user_id: int) -> None:
        tax = await self.repo.get_by_id(tax_id)
        if not tax:
            raise NotFoundException("Impuesto no encontrado")
        await self.audit.log_delete("Tax", tax.id, user_id, tax)
        await self.repo.delete(tax)
