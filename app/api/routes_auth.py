from fastapi import APIRouter, HTTPException, status, Body, Query
from typing import List
from pydantic import BaseModel
from app.models.user import UserRegister, UserLogin
from app.services.auth_service import register_user, login_user, get_user_profile, update_user_progress

router = APIRouter()

class ProgressUpdate(BaseModel):
    course_slug: str
    completed_lessons: List[int]

@router.post("/register")
async def register(user: UserRegister):
    return register_user(user)

@router.post("/login")
async def login(user: UserLogin):
    return login_user(user)

@router.get("/profile")
async def get_profile(token: str = Query(...)):
    return get_user_profile(token)

@router.post("/progress")
async def update_progress(
    token: str = Query(...),
    progress_data: ProgressUpdate = Body(...)
):
    """
    Обновление прогресса пользователя по курсу.
    """
    return update_user_progress(token, progress_data.course_slug, progress_data.completed_lessons)

@router.get("/debug")
async def debug():
    return {"status": "Маршруты работают"}
