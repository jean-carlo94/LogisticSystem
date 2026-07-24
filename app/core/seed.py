import json
from pathlib import Path

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.modules.roles.model import Permission, Role, RolePermission

SEED_PATH = Path(__file__).parent.parent / "seed.json"


async def seed_defaults():
    async with AsyncSessionLocal() as db:
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

        await db.commit()
