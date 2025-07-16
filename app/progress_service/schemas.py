from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class EnrollRequest(BaseModel):
    course_id: int

class ProgressOut(BaseModel):
    course_id: int
    progress_percent: float
    last_activity: Optional[datetime] = None
    streak_days: int
    completed_lessons: List[int] = []
    class Config:
        orm_mode = True

class LessonCompleteRequest(BaseModel):
    course_id: int
    content_id: int

class AssignmentSubmitRequest(BaseModel):
    submission: str
