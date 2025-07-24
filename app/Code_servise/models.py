from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from .db import Base  # предполагается, что Base импортируется из вашего db.py

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    difficulty = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    function_name = Column(String(100), nullable=True)  # добавить это поле

    tests = relationship("TaskTest", back_populates="task", cascade="all, delete-orphan")

class TaskTest(Base):
    __tablename__ = "task_tests"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    input_data = Column(Text, nullable=False)
    expected_output = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    order_index = Column(Integer, default=0)

    task = relationship("Task", back_populates="tests")
