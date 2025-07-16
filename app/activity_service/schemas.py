from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class QuestionCreate(BaseModel):
    course_id: int
    title: str
    body: Optional[str] = None

class AnswerCreate(BaseModel):
    body: str

class VoteRequest(BaseModel):
    vote_type: str  # expecting 'up' or 'down'

class QuestionOut(BaseModel):
    id: int
    user_id: int
    course_id: int
    title: str
    body: Optional[str] = None
    created_at: datetime
    class Config:
        orm_mode = True

class AnswerOut(BaseModel):
    id: int
    question_id: int
    user_id: int
    body: str
    created_at: datetime
    upvotes: int
    downvotes: int
    class Config:
        orm_mode = True

class QuestionDetailOut(QuestionOut):
    answers: List[AnswerOut] = []
