import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.database import _get_sessionmaker
from app.core.security import hash_password
from app.modules.roles.model import Permission, Role, RolePermission
from app.modules.users.model import User

SEED_PATH = Path(__file__).parent.parent / "seed.json"


async def seed_defaults():
    async with _get_sessionmaker()() as db:
        existing_perms = await db.scalars(select(Permission).limit(1))
        if existing_perms.first() is not None:
            return

        data = json.loads(SEED_PATH.read_text())

        for code, desc in data["permissions"].items():
            db.add(Permission(code=code, description=desc))

        await db.flush()

        admin_email = settings.ADMIN_EMAIL
        admin_password = settings.ADMIN_PASSWORD

        if admin_email and admin_password:
            admin = await db.scalar(
                select(User).where(User.email == admin_email)
            )
            if not admin:
                admin = User(
                    email=admin_email,
                    hashed_password=hash_password(admin_password),
                    first_name="Admin",
                    is_active=True,
                    is_super_admin=True,
                )
                db.add(admin)

        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()


async def seed_tenant_roles(tenant_id: int, db=None):
    from app.core.database import _get_sessionmaker

    data = json.loads(SEED_PATH.read_text())

    all_perm_codes = set(data["permissions"].keys())

    async def _seed(session):
        all_perms = await session.scalars(select(Permission))
        perm_map = {p.code: p.id for p in all_perms}

        for name, perms in data["roles"].items():
            unknown = [c for c in perms if c not in all_perm_codes]
            if unknown:
                raise ValueError(
                    f"Rol '{name}' referencia permisos no definidos: {unknown}"
                )

            existing = await session.scalar(
                select(Role).where(Role._name == name, Role.tenant_id == tenant_id)
            )
            if not existing:
                role = Role(name=name, description=f"Rol {name}", tenant_id=tenant_id)
                session.add(role)
                await session.flush()
                for code in perms:
                    session.add(RolePermission(
                        role_id=role.id,
                        permission_id=perm_map[code],
                    ))

        await session.flush()
        await session.commit()

    if db is not None:
        await _seed(db)
    else:
        async with _get_sessionmaker()() as session:
            await _seed(session)


DEFAULT_PAYMENT_METHODS = ["CASH", "CARD", "TRANSFER", "WALLET", "OTHER"]


async def seed_payment_methods(tenant_id: int, db=None):
    from app.core.database import _get_sessionmaker
    from app.modules.payments.model import PaymentMethod

    async def _seed(session):
        for name in DEFAULT_PAYMENT_METHODS:
            existing = await session.scalar(
                select(PaymentMethod).where(
                    PaymentMethod._name == name,
                    PaymentMethod.tenant_id == tenant_id,
                )
            )
            if not existing:
                session.add(PaymentMethod(
                    name=name,
                    tenant_id=tenant_id,
                    is_active=True,
                ))
        await session.flush()
        await session.commit()

    if db is not None:
        await _seed(db)
    else:
        async with _get_sessionmaker()() as session:
            await _seed(session)
