from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class ContentOut(BaseModel):
    id: int
    title: str
    content_type: Optional[str] = None
    content_url: Optional[str] = None
    order_index: Optional[int] = None
    duration_minutes: Optional[int] = None
    class Config:
        orm_mode = True

class ModuleOut(BaseModel):
    id: int
    title: str
    order_index: Optional[int] = None
    content_list: List[ContentOut] = []  # nested list of contents in this module
    class Config:
        orm_mode = True

class AssignmentOut(BaseModel):
    id: int
    title: str
    instructions: Optional[str] = None
    type: Optional[str] = None
    max_score: Optional[int] = None
    deadline: Optional[datetime] = None
    class Config:
        orm_mode = True

class CourseBase(BaseModel):
    slug: str
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    level: Optional[str] = None
    duration: Optional[str] = None

class CourseCreate(CourseBase):
    # When creating a course, maybe allow setting basic fields. author_id comes from token.
    pass

class CourseOut(CourseBase):
    id: int
    author_id: Optional[int] = None
    created_at: Optional[datetime] = None
    is_active: Optional[bool] = True
    modules: List[ModuleOut] = []
    assignments: List[AssignmentOut] = []
    class Config:
        orm_mode = True
