from app.core.audit import AuditLogger
from app.core.exceptions import ConflictException, NotFoundException
from app.core.pagination import PaginatedResponse
from app.modules.categories.model import Category
from app.modules.categories.repository import CategoryRepository
from app.modules.categories.schema import CategoryCreate, CategoryUpdate


class CategoryService:
    def __init__(self, repo: CategoryRepository, audit: AuditLogger):
        self.repo = repo
        self.audit = audit

    async def get_all(
        self, page: int = 1, size: int = 20, filters: dict | None = None
    ) -> PaginatedResponse[Category]:
        skip = (page - 1) * size
        items, total = await self.repo.get_all(skip=skip, limit=size, filters=filters)
        return PaginatedResponse.of(list(items), total, page, size)

    async def create(self, data: CategoryCreate, user_id: int) -> Category:
        if await self.repo.find_by_name(data.name):
            raise ConflictException("El nombre ya está en uso")
        category = await self.repo.create(**data.model_dump())
        await self.audit.log_create("Category", category.id, user_id, category)
        return category

    async def update(
        self, category_id: int, data: CategoryUpdate, user_id: int
    ) -> Category:
        category = await self.repo.get_by_id(category_id)
        if not category:
            raise NotFoundException("Categoría no encontrada")

        update_data = data.model_dump(exclude_unset=True)

        if "name" in update_data:
            existing = await self.repo.find_by_name(update_data["name"])
            if existing and existing.id != category_id:
                raise ConflictException("El nombre ya está en uso")

        await self.repo.update(category, **update_data)
        await self.audit.log_update("Category", category.id, user_id, update_data)
        return category

    async def delete(self, category_id: int, user_id: int) -> None:
        category = await self.repo.get_by_id(category_id)
        if not category:
            raise NotFoundException("Categoría no encontrada")

        await self.audit.log_delete("Category", category.id, user_id, category)
        await self.repo.delete(category)
