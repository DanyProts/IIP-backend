from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Interval
from sqlalchemy.orm import relationship
from .db import Base

class Course(Base):
    __tablename__ = "courses"
    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # references users table
    level = Column(String(20), nullable=True)
    created_at = Column(DateTime(timezone=False))
    is_active = Column(Boolean, default=True)
    duration = Column(String(50), nullable=True)
    # Relationships
    modules = relationship("CourseModule", back_populates="course", cascade="all, delete-orphan")
    assignments = relationship("Assignment", back_populates="course", cascade="all, delete-orphan")

class CourseModule(Base):
    __tablename__ = "course_modules"
    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id"))
    title = Column(String(200), nullable=False)
    order_index = Column(Integer)
    # Relationships
    course = relationship("Course", back_populates="modules")
    content_list = relationship("CourseContent", back_populates="module", cascade="all, delete-orphan")

class CourseContent(Base):
    __tablename__ = "course_content"
    id = Column(Integer, primary_key=True)
    module_id = Column(Integer, ForeignKey("course_modules.id"))
    title = Column(String(200), nullable=False)
    content_type = Column(String(20))       # e.g., "video", "text", etc.
    content_url = Column(Text, nullable=True)  # URL or path to content resource
    order_index = Column(Integer)
    duration_minutes = Column(Integer)
    # Relationships
    module = relationship("CourseModule", back_populates="content_list")

class Assignment(Base):
    __tablename__ = "assignments"
    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id"))
    title = Column(String(200), nullable=False)
    instructions = Column(Text, nullable=True)
    type = Column(String(20), nullable=True)  # e.g., "quiz" or "project"
    max_score = Column(Integer, nullable=True)
    deadline = Column(DateTime(timezone=False), nullable=True)
    # Relationships
    course = relationship("Course", back_populates="assignments")
