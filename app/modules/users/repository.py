from app.core.repository import BaseRepository
from app.modules.users.model import User


class UserRepository(BaseRepository):
    model = User

    async def find_by_email(self, email: str):
        return await User.find_by_email(self.db, email)
