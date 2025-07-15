from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import UserRegister, UserLogin, ProgressUpdate
from app.services.auth_service import register_user, login_user, get_user_profile, update_user_progress
from app.db.database import get_async_session

router = APIRouter()

@router.post("/register")
async def register(user: UserRegister, session: AsyncSession = Depends(get_async_session)):
    return await register_user(user, session)

@router.post("/login")
async def login(user: UserLogin, session: AsyncSession = Depends(get_async_session)):
    return await login_user(user, session)

@router.get("/profile")
async def profile(token: str = Query(...), session: AsyncSession = Depends(get_async_session)):
    return await get_user_profile(token, session)

@router.post("/progress")
async def progress(token: str = Query(...), progress_data: ProgressUpdate = Body(...), session: AsyncSession = Depends(get_async_session)):
    return await update_user_progress(token, progress_data.course_slug, progress_data.completed_lessons, session)

@router.get("/debug")
async def debug():
    return {"status": "Маршруты работают"}
