from app.core.repository import BaseRepository
from app.modules.products.model import Product


class ProductRepository(BaseRepository):
    model = Product
