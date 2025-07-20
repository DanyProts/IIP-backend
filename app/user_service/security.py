from passlib.context import CryptContext
from datetime import datetime, timedelta
import jwt

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = "SUPER_SECRET_JWT_KEY"  # Секретный ключ, нужно менять
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
