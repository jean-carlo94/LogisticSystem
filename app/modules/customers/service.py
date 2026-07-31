from __future__ import annotations

from app.core.audit import AuditLogger
from app.core.exceptions import NotFoundException, ValidationException
from app.core.pagination import PaginatedResponse
from app.core.tenant import current_tenant_id
from app.modules.customers.model import Customer
from app.modules.customers.repository import CustomerRepository
from app.modules.customers.schema import CustomerCreate, CustomerUpdate


class CustomerService:
    def __init__(self, repo: CustomerRepository, audit: AuditLogger):
        self.repo = repo
        self.audit = audit

    async def get_all(
        self, page: int = 1, size: int = 20, filters: dict | None = None
    ) -> PaginatedResponse[Customer]:
        skip = (page - 1) * size
        items, total = await self.repo.get_all(skip=skip, limit=size, filters=filters)
        return PaginatedResponse.of(list(items), total, page, size)

    async def create(self, data: CustomerCreate, user_id: int) -> Customer:
        if current_tenant_id.get() is None:
            raise ValidationException("Debe especificar un tenant (use header X-Tenant)")
        customer = await self.repo.create(**data.model_dump())
        await self.audit.log_create("Customer", customer.id, user_id, customer)
        return customer

    async def update(self, customer_id: int, data: CustomerUpdate, user_id: int) -> Customer:
        customer = await self.repo.get_by_id(customer_id)
        if not customer:
            raise NotFoundException("Cliente no encontrado")
        update_data = data.model_dump(exclude_unset=True)
        await self.repo.update(customer, **update_data)
        await self.audit.log_update("Customer", customer.id, user_id, update_data)
        return customer

    async def get_by_id(self, customer_id: int) -> Customer:
        customer = await self.repo.get_by_id(customer_id)
        if not customer:
            raise NotFoundException("Cliente no encontrado")
        return customer

    async def find_or_create(self, data: dict, user_id: int) -> Customer | None:
        email = data.get("customer_email")
        document = data.get("customer_document")
        name = data.get("customer_name", "")

        if not email and not document:
            return None

        customer = None
        if email:
            customer = await self.repo.find_by_email(email)
        if not customer and document:
            customer = await self.repo.find_by_document(document)

        if customer:
            if customer.name != name:
                await self.repo.update(customer, name=name)
            return customer

        customer = await self.repo.create(
            name=name,
            email=email,
            phone=data.get("customer_phone"),
            document=document,
            address=data.get("customer_address"),
        )
        await self.audit.log_create("Customer", customer.id, user_id, customer)
        return customer
