from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

class UserRegister(BaseModel):
    email: EmailStr
    name: str
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class ProgressUpdate(BaseModel):
    course_slug: str
    completed_lessons: List[int]

class EnrolledCourse(BaseModel):
    slug: str
    progress: float
    completedLessons: List[int]
    lastActivity: Optional[str]

class UserActivityItem(BaseModel):
    day: str
    count: int
    details: List[str]

class UserProfile(BaseModel):
    id: int
    name: str
    email: str
    joinDate: Optional[str]
    lastVisit: Optional[str]
    stats: dict
    enrolledCourses: List[EnrolledCourse]
    activity: dict

