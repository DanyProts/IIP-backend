from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime
from .. import models, schemas, security, db
import jwt  # импорт jwt

router = APIRouter(tags=["Authentication"])

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
        role="student"
    )
    new_user.join_date = datetime.utcnow()
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

@router.post("/login", response_model=schemas.Token)
async def login(form: schemas.UserLogin, db: AsyncSession = Depends(db.get_db)):
    result = await db.execute(select(models.User).filter(models.User.email == form.email))
    user = result.scalars().first()

    if not user or not security.verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user.last_visit = datetime.utcnow()
    await db.commit()

    token_data = {"user_id": user.id, "role": user.role}
    token = security.create_access_token(token_data)
    return {"access_token": token, "token_type": "bearer"}

from fastapi.security import OAuth2PasswordBearer
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

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
