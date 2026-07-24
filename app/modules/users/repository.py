from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.users.model import User


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_by_email(self, email: str):
        return await User.find_by_email(self.db, email)

    async def create(self, **kwargs):
        return await User.create(self.db, **kwargs)
