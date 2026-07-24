import json
from pathlib import Path

from sqlalchemy import select

from app.core.database import _get_sessionmaker
from app.core.security import hash_password
from app.modules.roles.model import Permission, Role, RolePermission, UserRole
from app.modules.users.model import User

SEED_PATH = Path(__file__).parent.parent / "seed.json"


async def seed_defaults():
    async with _get_sessionmaker()() as db:
        count = await db.scalar(select(Permission).limit(1))
        if count is not None:
            return

        data = json.loads(SEED_PATH.read_text())

        perm_map = {}
        for code, desc in data["permissions"].items():
            p = Permission(code=code, description=desc)
            db.add(p)
            await db.flush()
            perm_map[code] = p.id

        for name, perms in data["roles"].items():
            role = Role(name=name, description=f"Rol {name}")
            db.add(role)
            await db.flush()
            for code in perms:
                db.add(RolePermission(role_id=role.id, permission_id=perm_map[code]))

        admin_role = await db.scalar(select(Role).where(Role.name == "Admin"))
        admin = User(
            email="admin@logistics.com",
            hashed_password=hash_password("admin123"),
            first_name="Admin",
            is_active=True,
            is_super_admin=True,
        )
        db.add(admin)
        await db.flush()
        if admin_role:
            db.add(UserRole(user_id=admin.id, role_id=admin_role.id))

        await db.commit()
