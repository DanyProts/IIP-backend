from sqlalchemy import Column, Integer, String, Text, DateTime, func
from .db import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False, unique=True, index=True)
    password_hash = Column(Text, nullable=False)
    role = Column(String(20), default="student")  # e.g., 'student' or 'admin'
    avatar_url = Column(Text, nullable=True)
    join_date = Column(DateTime(timezone=False), server_default=func.now())
    last_visit = Column(DateTime(timezone=False), nullable=True)
