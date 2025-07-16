from sqlalchemy import Column, Integer, Numeric, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY
from .db import Base

class UserCourseEnrollment(Base):
    __tablename__ = "user_course_enrollment"
    user_id = Column(Integer, primary_key=True)
    course_id = Column(Integer, primary_key=True)
    enrolled_at = Column(DateTime(timezone=False))

class UserCourseProgress(Base):
    __tablename__ = "user_course_progress"
    user_id = Column(Integer, primary_key=True)
    course_id = Column(Integer, primary_key=True)
    progress_percent = Column(Numeric(5,2), default=0.00)
    last_activity = Column(DateTime(timezone=False), nullable=True)
    completed_lessons = Column(ARRAY(Integer), default=[])  # list of completed content IDs
    total_time_minutes = Column(Integer, default=0)
    streak_days = Column(Integer, default=0)

class LessonCompletion(Base):
    __tablename__ = "lesson_completion"
    user_id = Column(Integer, primary_key=True)
    content_id = Column(Integer, primary_key=True)
    completed_at = Column(DateTime(timezone=False))

class UserAssignment(Base):
    __tablename__ = "user_assignments"
    user_id = Column(Integer, primary_key=True)
    assignment_id = Column(Integer, primary_key=True)
    submission = Column(Text, nullable=True)
    submitted_at = Column(DateTime(timezone=False))
    score = Column(Integer, nullable=True)
    feedback = Column(Text, nullable=True)
