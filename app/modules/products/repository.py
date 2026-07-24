from app.modules.products.model import Product
from app.modules.products.schema import ProductCreate, ProductUpdate


class ProductRepository:
    def __init__(self, db):
        self.db = db

    def get_all(self, skip=0, limit=100):
        return Product.get_all(self.db, skip=skip, limit=limit)

    def get_by_id(self, product_id: int) -> Product | None:
        return Product.get_id(self.db, product_id)

    def create(self, product_in: ProductCreate) -> Product:
        return Product.create(self.db, **product_in.model_dump())

    def update(self, product: Product, product_in: ProductUpdate) -> Product:
        update_data = product_in.model_dump(exclude_unset=True)
        return product.update(self.db, **update_data)

    def delete(self, product: Product) -> None:
        product.delete(self.db)
