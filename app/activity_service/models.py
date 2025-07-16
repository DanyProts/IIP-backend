from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from .db import Base

class UserActivityLog(Base):
    __tablename__ = "user_activity_log"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    action = Column(String(100), nullable=False)
    related_object_type = Column(String(50), nullable=True)
    related_object_id = Column(Integer, nullable=True)
    timestamp = Column(DateTime(timezone=False))

class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=True)
    course_id = Column(Integer, ForeignKey("courses.id"))
    created_at = Column(DateTime(timezone=False))

class Answer(Base):
    __tablename__ = "answers"
    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    body = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=False))
    upvotes = Column(Integer, default=0)
    downvotes = Column(Integer, default=0)

class Vote(Base):
    __tablename__ = "votes"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    answer_id = Column(Integer, ForeignKey("answers.id"))
    vote_type = Column(String(10), nullable=False)  # 'up' or 'down'
