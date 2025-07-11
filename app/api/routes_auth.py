from fastapi import APIRouter, HTTPException, status
from app.models.user import UserRegister, UserLogin
from app.services.auth_service import register_user, login_user, get_user_profile

router = APIRouter()

@router.post("/register")
async def register(user: UserRegister):
    return register_user(user)

@router.post("/login")
async def login(user: UserLogin):
    return login_user(user)

@router.get("/profile")
async def get_profile(token: str):
    return get_user_profile(token)

@router.get("/debug")
async def debug():
    return {"status": "Маршруты работают"}
