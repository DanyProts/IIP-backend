from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    name: str
    email: EmailStr

class UserCreate(UserBase):
    password: str  # plaintext password for registration

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(UserBase):
    id: int
    role: str
    avatar_url: Optional[str] = None
    join_date: Optional[datetime] = None
    last_visit: Optional[datetime] = None

    class Config:
        from_attributes = True  # Pydantic v2; если v1 — заменить на orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
