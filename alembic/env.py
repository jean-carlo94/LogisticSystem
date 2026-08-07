from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from sqlalchemy import create_engine

from alembic import context

from app.core.config import settings
from app.core.database import Base

from app.modules.products.model import Product
from app.modules.events.model import Event
from app.modules.users.model import AccountActivation, PasswordResetToken, User
from app.modules.roles.model import Permission, Role, RolePermission, UserRole
from app.modules.shelves.model import Shelf, ShelfItem
from app.modules.categories.model import Category, ProductCategory
from app.modules.sales.model import Sale, SaleItem
from app.modules.invoice_templates.model import InvoiceTemplate
from app.modules.orders.model import Order, OrderItem
from app.modules.tenants.model import Tenant
from app.modules.taxes.model import ProductTax, Tax
from app.modules.customers.model import Customer
from app.modules.payments.model import Payment
from app.modules.cash_register.model import CashRegisterSession
from app.modules.stations.model import Station, StationSession, StationSessionItem
from app.modules.tenant_config.model import TenantConfig
from app.modules.api_keys.model import ApiKey


config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(settings.DATABASE_URL, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
