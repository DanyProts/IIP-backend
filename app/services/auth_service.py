from fastapi import HTTPException, status
from app.models.user import UserRegister, UserLogin
from app.db.iipdb import users_db
import secrets
import logging

logger = logging.getLogger(__name__)

def register_user(user: UserRegister):
    if user.email in users_db:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    
    users_db[user.email] = user.dict()
    logger.info(f"User registered: {user.email}")
    return {"status": "success", "message": "Registration successful", "email": user.email}

def login_user(user: UserLogin):
    if user.email not in users_db or users_db[user.email]["password"] != user.password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    
    token = secrets.token_hex(16)
    return {
        "status": "success",
        "token": token,
        "user": {
            "email": user.email,
            "firstName": users_db[user.email]["firstName"],
            "lastName": users_db[user.email]["lastName"]
        }
    }
