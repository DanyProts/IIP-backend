from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    name: str
    email: str

class UserCreate(UserBase):
    password: str  # plaintext password for registration

class UserOut(UserBase):
    id: int
    role: str
    avatar_url: Optional[str] = None
    join_date: Optional[datetime] = None
    last_visit: Optional[datetime] = None

    class Config:
        orm_mode = True  # Allows ORM model instances to be converted to this schema

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
