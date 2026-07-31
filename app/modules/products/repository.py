from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.core.repository import BaseRepository
from app.core.exceptions import NotFoundException
from app.modules.products.model import Product


class ProductRepository(BaseRepository):
    model = Product

    async def find_by_barcode(self, barcode: str) -> Product | None:
        stmt = select(Product).where(Product._barcode == barcode)
        if self._tenant_id is not None:
            stmt = stmt.where(Product.tenant_id == self._tenant_id)
        return await self.db.scalar(stmt)

    async def get_product_shelves(self, product_id: int):
        from app.modules.shelves.model import Shelf, ShelfItem

        stmt = select(Shelf).join(ShelfItem, ShelfItem.shelf_id == Shelf.id).where(
            ShelfItem.product_id == product_id
        )
        if self._tenant_id is not None:
            stmt = stmt.where(Shelf.tenant_id == self._tenant_id)
        result = await self.db.scalars(stmt)
        return result.all()

    async def validate_category_ids(self, category_ids: list[int]) -> None:
        from app.modules.categories.model import Category

        stmt = select(func.count(Category.id)).where(Category.id.in_(category_ids))
        if self._tenant_id is not None:
            stmt = stmt.where(Category.tenant_id == self._tenant_id)
        existing = await self.db.scalar(stmt)
        if existing != len(category_ids):
            stmt_ids = select(Category.id).where(Category.id.in_(category_ids))
            if self._tenant_id is not None:
                stmt_ids = stmt_ids.where(Category.tenant_id == self._tenant_id)
            existing_ids = await self.db.scalars(stmt_ids)
            found = set(existing_ids.all())
            missing = set(category_ids) - found
            raise NotFoundException(f"Categorías no encontradas: {missing}")

    async def set_product_categories(
        self, product_id: int, category_ids: list[int]
    ) -> None:
        from app.modules.categories.model import ProductCategory

        if category_ids:
            await self.validate_category_ids(category_ids)

        existing = await self.db.scalars(
            select(ProductCategory).where(ProductCategory.product_id == product_id)
        )
        for pc in existing:
            await self.db.delete(pc)

        if existing:
            await self.db.flush()

        for cat_id in category_ids:
            self.db.add(ProductCategory(product_id=product_id, category_id=cat_id))

        await self.db.flush()

    async def get_by_id_with_categories(self, product_id: int) -> Product | None:
        return await self.db.scalar(
            select(Product)
            .where(Product.id == product_id)
            .options(selectinload(Product.categories), selectinload(Product.taxes))
            .execution_options(populate_existing=True)
        )

    async def validate_tax_ids(self, tax_ids: list[int]) -> None:
        from app.modules.taxes.model import Tax

        stmt = select(func.count(Tax.id)).where(Tax.id.in_(tax_ids))
        if self._tenant_id is not None:
            stmt = stmt.where(Tax.tenant_id == self._tenant_id)
        existing = await self.db.scalar(stmt)
        if existing != len(tax_ids):
            stmt_ids = select(Tax.id).where(Tax.id.in_(tax_ids))
            if self._tenant_id is not None:
                stmt_ids = stmt_ids.where(Tax.tenant_id == self._tenant_id)
            existing_ids = await self.db.scalars(stmt_ids)
            found = set(existing_ids.all())
            missing = set(tax_ids) - found
            raise NotFoundException(f"Impuestos no encontrados: {missing}")

    async def set_product_taxes(self, product_id: int, tax_ids: list[int]) -> None:
        from app.modules.taxes.model import ProductTax

        if tax_ids:
            await self.validate_tax_ids(tax_ids)

        existing = await self.db.scalars(
            select(ProductTax).where(ProductTax.product_id == product_id)
        )
        for pt in existing:
            await self.db.delete(pt)

        if existing:
            await self.db.flush()

        for tax_id in tax_ids:
            self.db.add(ProductTax(product_id=product_id, tax_id=tax_id))

        await self.db.flush()

    async def get_product_locations(self, product_id: int):
        from app.modules.shelves.model import Shelf, ShelfItem

        stmt = select(ShelfItem).where(ShelfItem.product_id == product_id)
        if self._tenant_id is not None:
            stmt = stmt.join(Shelf, Shelf.id == ShelfItem.shelf_id).where(
                Shelf.tenant_id == self._tenant_id
            )
        items = await self.db.scalars(stmt)
        shelf_items = items.all()

        if not shelf_items:
            return []

        shelf_ids = [si.shelf_id for si in shelf_items]
        stmt = select(Shelf).where(Shelf.id.in_(shelf_ids))
        if self._tenant_id is not None:
            stmt = stmt.where(Shelf.tenant_id == self._tenant_id)
        shelves_result = await self.db.scalars(stmt)
        shelves_map = {s.id: s for s in shelves_result}

        return [
            (si, shelves_map.get(si.shelf_id))
            for si in shelf_items
            if si.quantity > 0
        ]

    async def has_sale_history(self, product_id: int) -> bool:
        from app.modules.sales.model import SaleItem

        item = await self.db.scalar(
            select(SaleItem.id).where(SaleItem.product_id == product_id).limit(1)
        )
        return item is not None

    async def has_order_history(self, product_id: int) -> bool:
        from app.modules.orders.model import OrderItem

        item = await self.db.scalar(
            select(OrderItem.id).where(OrderItem.product_id == product_id).limit(1)
        )
        return item is not None

    async def get_product_taxes(self, product_id: int):
        from app.modules.taxes.model import Tax, ProductTax

        stmt = (
            select(Tax)
            .join(ProductTax, ProductTax.tax_id == Tax.id)
            .where(ProductTax.product_id == product_id, Tax.is_active == True)
        )
        if self._tenant_id is not None:
            stmt = stmt.where(Tax.tenant_id == self._tenant_id)
        result = await self.db.scalars(stmt)
        return result.all()

    async def get_products_taxes_batch(self, product_ids: list[int]) -> dict[int, list]:
        from app.modules.taxes.model import Tax, ProductTax

        stmt = (
            select(ProductTax.product_id, Tax)
            .join(Tax, ProductTax.tax_id == Tax.id)
            .where(ProductTax.product_id.in_(product_ids), Tax.is_active == True)
        )
        if self._tenant_id is not None:
            stmt = stmt.where(Tax.tenant_id == self._tenant_id)
        rows = (await self.db.execute(stmt)).all()
        result: dict[int, list] = {pid: [] for pid in product_ids}
        for pid, tax in rows:
            result[pid].append(tax)
        return result

    async def lock_products_for_update(self, product_ids: list[int]) -> dict[int, "Product"]:
        from sqlalchemy import update as sa_update

        stmt = (
            select(Product)
            .where(Product.id.in_(product_ids))
            .with_for_update()
        )
        if self._tenant_id is not None:
            stmt = stmt.where(Product.tenant_id == self._tenant_id)
        rows = (await self.db.scalars(stmt)).all()
        return {p.id: p for p in rows}
