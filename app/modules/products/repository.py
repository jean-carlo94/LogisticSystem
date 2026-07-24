from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.products.model import Product


class ProductRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self, skip=0, limit=100):
        return await Product.get_all(self.db, skip=skip, limit=limit)

    async def get_by_id(self, product_id: int):
        return await Product.get_id(self.db, product_id)

    async def create(self, **kwargs):
        return await Product.create(self.db, **kwargs)

    async def update(self, product: Product, **kwargs):
        return await product.update(self.db, **kwargs)

    async def delete(self, product: Product):
        await product.delete(self.db)
