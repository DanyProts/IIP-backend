from sqlalchemy import (
    Column, Integer, String, Text, Boolean, ForeignKey, DateTime, Float, func
)
from sqlalchemy.orm import relationship
from datetime import datetime
from .db import Base  # Ваш Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False, unique=True, index=True)
    password_hash = Column(Text, nullable=False)
    role = Column(String(20), default="student")  # например, 'student' или 'admin'
    avatar_url = Column(Text, nullable=True)
    join_date = Column(DateTime(timezone=False), server_default=func.now())
    last_visit = Column(DateTime(timezone=False), nullable=True)
    is_verified = Column(Boolean, default=False, nullable=False)
    verification_code = Column(String(32), nullable=True)
    verification_code_expiry = Column(DateTime, nullable=True)

    solved_tasks = relationship("UserSolvedTask", back_populates="user", cascade="all, delete-orphan")
    favorite_tasks = relationship("UserFavoriteTask", back_populates="user", cascade="all, delete-orphan")
    submissions = relationship("Submission", back_populates="user", cascade="all, delete-orphan")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    difficulty = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    function_name = Column(String(100), nullable=True)

    tests = relationship("TaskTest", back_populates="task", cascade="all, delete-orphan")
    solved_tasks = relationship("UserSolvedTask", back_populates="task", cascade="all, delete-orphan")
    favorite_tasks = relationship("UserFavoriteTask", back_populates="task", cascade="all, delete-orphan")
    submissions = relationship("Submission", back_populates="task", cascade="all, delete-orphan")


class TaskTest(Base):
    __tablename__ = "task_tests"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    input_data = Column(Text, nullable=False)
    expected_output = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    order_index = Column(Integer, default=0)

    task = relationship("Task", back_populates="tests")


class UserSolvedTask(Base):
    __tablename__ = "user_solved_tasks"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True)
    solved_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="solved_tasks")
    task = relationship("Task", back_populates="solved_tasks")


class UserFavoriteTask(Base):
    __tablename__ = "user_favorite_tasks"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True)
    added_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="favorite_tasks")
    task = relationship("Task", back_populates="favorite_tasks")


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    code = Column(Text, nullable=False)
    language = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False)  # Например, 'Accepted', 'Wrong Answer', 'Runtime Error'
    output = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    runtime = Column(Float, nullable=True)  # Время выполнения в секундах или миллисекундах
    memory = Column(Float, nullable=True)   # Использование памяти в мегабайтах
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="submissions")
    task = relationship("Task", back_populates="submissions")
