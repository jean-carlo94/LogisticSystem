from fastapi import APIRouter

from app.modules.categories.router import router as categories_router
from app.modules.events.router import router as events_router
from app.modules.orders.router import router as orders_router
from app.modules.products.router import router as products_router
from app.modules.roles.router import router as roles_router
from app.modules.sales.router import router as sales_router
from app.modules.shelves.router import router as shelves_router
from app.modules.users.router import auth_router, users_router

router = APIRouter()
router.include_router(products_router)
router.include_router(events_router)
router.include_router(auth_router)
router.include_router(users_router)
router.include_router(roles_router)
router.include_router(shelves_router)
router.include_router(categories_router)
router.include_router(sales_router)
router.include_router(orders_router)
