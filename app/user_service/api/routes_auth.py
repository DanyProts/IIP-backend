from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime
import random
import smtplib
from email.message import EmailMessage
from .. import models, schemas, security, db
import jwt
from fastapi.security import OAuth2PasswordBearer
import os
from pathlib import Path
from dotenv import load_dotenv

root = Path(__file__).resolve().parents[2]
load_dotenv(dotenv_path=root / ".env")

EMAIL_ADDRESS = os.getenv("SMTP_EMAIL")
EMAIL_PASSWORD = os.getenv("SMTP_PASSWORD")

router = APIRouter(tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# --- Вспомогательные функции ---

def generate_verification_code(length: int = 6) -> str:
    return ''.join(str(random.randint(0, 9)) for _ in range(length))

def send_verification_email(to_email: str, code: str):
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        raise RuntimeError("Email configuration is not set")

    msg = EmailMessage()
    msg['Subject'] = "Подтверждение Email"
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = to_email
    msg.set_content(f"Ваш код подтверждения: {code}")

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)

# --- Роуты ---

@router.post("/register", response_model=schemas.UserOut, status_code=201)
async def register(user_data: schemas.UserCreate, db: AsyncSession = Depends(db.get_db)):
    # Проверяем, есть ли пользователь с таким email
    result = await db.execute(select(models.User).filter(models.User.email == user_data.email))
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email is already registered")

    new_user = models.User(
        name=user_data.name,
        email=user_data.email,
        password_hash=security.get_password_hash(user_data.password),
        role="student",
        is_verified=False,  # пользователь не подтвержден по умолчанию
        verification_code=generate_verification_code()
    )
    new_user.join_date = datetime.utcnow()
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Отправляем код подтверждения на email
    send_verification_email(new_user.email, new_user.verification_code)

    return new_user


@router.post("/verify-email", status_code=200)
async def verify_email(email: str = Body(...), code: str = Body(...), db: AsyncSession = Depends(db.get_db)):
    result = await db.execute(select(models.User).filter(models.User.email == email))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_verified:
        return {"message": "Email already verified"}

    if user.verification_code != code:
        raise HTTPException(status_code=400, detail="Invalid verification code")

    user.is_verified = True
    user.verification_code = None
    await db.commit()

    return {"message": "Email verified successfully"}


@router.post("/login", response_model=schemas.Token)
async def login(form: schemas.UserLogin, db: AsyncSession = Depends(db.get_db)):
    result = await db.execute(select(models.User).filter(models.User.email == form.email))
    user = result.scalars().first()

    if not user or not security.verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Проверяем подтверждение email
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Email is not verified")

    user.last_visit = datetime.utcnow()
    await db.commit()

    token_data = {"user_id": user.id, "role": user.role}
    token = security.create_access_token(token_data)
    return {"access_token": token, "token_type": "bearer"}


async def get_current_user(db: AsyncSession = Depends(db.get_db), token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication token")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Could not validate token")

    result = await db.execute(select(models.User).filter(models.User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/users/me", response_model=schemas.UserOut)
async def read_current_user(current_user: models.User = Depends(get_current_user)):
    return current_user
