from sqlalchemy import Column, Integer, String, Text, DateTime, func, Numeric, ARRAY, ForeignKey
from datetime import datetime
from sqlalchemy import Boolean
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
    is_verified = Column(Boolean, default=False, nullable=False)
    verification_code = Column(String(32), nullable=True)
    verification_code_expiry = Column(DateTime, nullable=True)


class UserCourseEnrollment(Base):
    __tablename__ = "user_course_enrollment"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id"), primary_key=True)
    enrolled_at = Column(DateTime, default=datetime.utcnow)

class UserCourseProgress(Base):
    __tablename__ = "user_course_progress"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id"), primary_key=True)
    progress_percent = Column(Numeric(5, 2), default=0.0)
    last_activity = Column(DateTime, nullable=True)
    completed_lessons = Column(ARRAY(Integer), default=[])
    total_time_minutes = Column(Integer, default=0)
    streak_days = Column(Integer, default=0)