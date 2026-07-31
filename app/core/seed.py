import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.database import _get_sessionmaker
from app.core.security import hash_password
from app.modules.roles.model import Permission, Role, RolePermission, UserRole
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

        all_perms = await db.scalars(select(Permission))
        perm_map = {p.code: p.id for p in all_perms}

        all_perm_codes = set(perm_map.keys())

        for name, perms in data["roles"].items():
            unknown = [c for c in perms if c not in all_perm_codes]
            if unknown:
                raise ValueError(
                    f"Rol '{name}' referencia permisos no definidos: {unknown}"
                )

            existing_role = await db.scalar(select(Role).where(Role.name == name))
            if existing_role:
                existing_role_perms = await db.scalars(
                    select(RolePermission.permission_id).where(
                        RolePermission.role_id == existing_role.id
                    )
                )
                existing_perm_ids = set(existing_role_perms.all())
                for code in perms:
                    if perm_map[code] not in existing_perm_ids:
                        db.add(RolePermission(
                            role_id=existing_role.id,
                            permission_id=perm_map[code],
                        ))
            else:
                role = Role(name=name, description=f"Rol {name}")
                db.add(role)
                await db.flush()
                for code in perms:
                    db.add(RolePermission(
                        role_id=role.id,
                        permission_id=perm_map[code],
                    ))

        admin_email = settings.ADMIN_EMAIL or "admin@alunatechnologies.com"
        admin_password = settings.ADMIN_PASSWORD or "admin123"

        if admin_email and admin_password:
            admin = await db.scalar(
                select(User).where(User.email == admin_email)
            )
            if not admin:
                admin_role = await db.scalar(select(Role).where(Role.name == "Admin"))
                admin = User(
                    email=admin_email,
                    hashed_password=hash_password(admin_password),
                    first_name="Admin",
                    is_active=True,
                    is_super_admin=True,
                )
                db.add(admin)
                await db.flush()
                if admin_role:
                    db.add(UserRole(user_id=admin.id, role_id=admin_role.id))

        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
