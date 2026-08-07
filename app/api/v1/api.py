from fastapi import APIRouter

from app.modules.api_keys.router import router as api_keys_router
from app.modules.cash_register.router import router as cash_register_router, registers_router
from app.modules.categories.router import router as categories_router
from app.modules.customers.router import router as customers_router
from app.modules.events.router import router as events_router
from app.modules.invoice_templates.router import template_router as invoice_templates_router, invoice_router
from app.modules.orders.router import router as orders_router
from app.modules.payments.router import router as payments_router
from app.modules.products.router import router as products_router
from app.modules.roles.router import router as roles_router
from app.modules.sales.router import router as sales_router
from app.modules.shelves.router import router as shelves_router
from app.modules.stations.router import router as stations_router
from app.modules.taxes.router import router as taxes_router
from app.modules.tenant_config.router import router as tenant_config_router
from app.modules.tenants.router import router as tenants_router
from app.modules.users.router import auth_router, users_router

router = APIRouter()
router.include_router(api_keys_router)
router.include_router(tenants_router)
router.include_router(tenant_config_router)
router.include_router(taxes_router)
router.include_router(customers_router)
router.include_router(products_router)
router.include_router(events_router)
router.include_router(auth_router)
router.include_router(users_router)
router.include_router(roles_router)
router.include_router(shelves_router)
router.include_router(categories_router)
router.include_router(sales_router)
router.include_router(orders_router)
router.include_router(payments_router)
router.include_router(cash_register_router)
router.include_router(registers_router)
router.include_router(stations_router)
router.include_router(invoice_templates_router)
router.include_router(invoice_router)
