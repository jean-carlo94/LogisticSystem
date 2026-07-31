from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_audit_logger
from app.core.audit import AuditLogger
from app.core.database import get_db
from app.modules.orders.repository import OrderItemRepository, OrderRepository
from app.modules.orders.service import OrderService
from app.modules.products.repository import ProductRepository
from app.modules.sales.repository import SaleItemRepository, SaleRepository
from app.modules.sales.service import SaleService
from app.modules.shelves.repository import ShelfItemRepository, ShelfRepository


async def get_order_service(
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> OrderService:
    sale_service = SaleService(
        SaleRepository(db),
        SaleItemRepository(db),
        ShelfItemRepository(db),
        ShelfRepository(db),
        ProductRepository(db),
        audit,
    )
    return OrderService(
        OrderRepository(db),
        OrderItemRepository(db),
        ShelfItemRepository(db),
        audit,
        sale_service,
    )
