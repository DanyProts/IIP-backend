from sqlalchemy import (
    Column, Integer, String, DateTime, Float, ForeignKey, Boolean, Text, Numeric, ARRAY, func
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from datetime import datetime
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(Text, nullable=False)
    role = Column(String(20), default="student")
    avatar_url = Column(Text, nullable=True)
    join_date = Column(DateTime, nullable=True, default=func.now())
    last_visit = Column(DateTime, nullable=True, default=func.now())

    # Убраны поля, которых нет в таблице users
    # total_time_minutes = ...
    # streak_days = ...
    # completed_lessons = ...

    enrollments = relationship("UserCourseEnrollment", back_populates="user")
    progress = relationship("UserCourseProgress", back_populates="user")
    activity_logs = relationship("UserActivityLog", back_populates="user")


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    level = Column(String(20), nullable=True)
    created_at = Column(DateTime, nullable=True, default=func.now())
    is_active = Column(Boolean, default=True)
    duration = Column(String(50), nullable=True)

    enrollments = relationship("UserCourseEnrollment", back_populates="course")
    progress = relationship("UserCourseProgress", back_populates="course")
    modules = relationship("CourseModule", back_populates="course")


class UserCourseEnrollment(Base):
    __tablename__ = "user_course_enrollment"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id"), primary_key=True)
    enrolled_at = Column(DateTime, default=func.now())

    user = relationship("User", back_populates="enrollments")
    course = relationship("Course", back_populates="enrollments")


class UserCourseProgress(Base):
    __tablename__ = "user_course_progress"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id"), primary_key=True)
    progress_percent = Column(Numeric(5, 2), default=0.0)
    last_activity = Column(DateTime, default=func.now())
    completed_lessons = Column(PG_ARRAY(Integer), default=[])  # массив integer, в PostgreSQL

    total_time_minutes = Column(Integer, default=0)
    streak_days = Column(Integer, default=0)

    user = relationship("User", back_populates="progress")
    course = relationship("Course", back_populates="progress")


class UserActivityLog(Base):
    __tablename__ = "user_activity_log"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String(100), nullable=False)
    related_object_type = Column(String(50), nullable=True)
    related_object_id = Column(Integer, nullable=True)
    timestamp = Column(DateTime, default=func.now())

    user = relationship("User", back_populates="activity_logs")
class CourseModule(Base):
    __tablename__ = "course_modules"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    order = Column(Integer, default=0)

    course = relationship("Course", back_populates="modules")
    contents = relationship("CourseContent", back_populates="module")


class CourseContent(Base):
    __tablename__ = "course_content"

    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(Integer, ForeignKey("course_modules.id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    duration = Column(String(50), nullable=True)
    order = Column(Integer, default=0)

    module = relationship("CourseModule", back_populates="contents")

