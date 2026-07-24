from app.modules.users.model import User
from app.modules.users.schema import UserCreate


class UserRepository:
    def __init__(self, db):
        self.db = db

    def get_by_email(self, email: str) -> User | None:
        return User.find_by_email(self.db, email)

    def create(self, user_in: UserCreate, hashed_password: str) -> User:
        return User.create(
            self.db, email=user_in.email, hashed_password=hashed_password
        )
