from typing import List, Optional
from datetime import datetime, timezone
from app.services.firestore import FirestoreService
from app.api.schemas.user import UserResponse, UserCreate
from pydantic import BaseModel, EmailStr

class UserModel(UserResponse):
    """Internal user model for Firestore storage."""
    password_hash: str
    updated_at: datetime

class UserFirestoreService(FirestoreService[UserModel]):
    def __init__(self):
        super().__init__("users", UserModel)

    async def get_by_email(self, email: str) -> Optional[UserModel]:
        users = await self.list(filters=[("email", "==", email)], limit=1)
        return users[0] if users else None

    async def create_user(self, user_in: UserCreate, password_hash: str) -> UserModel:
        now = datetime.now(timezone.utc)
        user = UserModel(
            id="", # Will be set by Firestore
            email=user_in.email,
            full_name=user_in.full_name,
            password_hash=password_hash,
            is_active=True,
            is_verified=False,
            subscription_tier="free",
            created_at=now,
            updated_at=now
        )
        return await self.create(user)

user_service = UserFirestoreService()
