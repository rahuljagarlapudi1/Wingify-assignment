from datetime import datetime
from typing import Optional
from enum import Enum
from beanie import Document
from pydantic import Field, EmailStr

class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"

class User(Document):
    email: EmailStr = Field(..., unique=True)
    username: str = Field(..., unique=True, min_length=3, max_length=50)
    full_name: str = Field(..., min_length=1, max_length=100)
    hashed_password: str = Field(...)
    role: UserRole = Field(default=UserRole.USER)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = Field(default=None)
    
    class Settings:
        name = "users"
        indexes = [
            [("email", 1)],
            [("username", 1)],
            [("created_at", -1)],
        ]
