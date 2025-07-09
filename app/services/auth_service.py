from fastapi import HTTPException, status, Depends
from app.models.user import UserRegister, UserLogin
from passlib.context import CryptContext
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
import secrets
from typing import Dict, Any
from app.db.db_config import host, user, db_name, password

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_db_connection():
    return psycopg2.connect(
        host=host,
        database=db_name,
        user=user,
        password=password,
        cursor_factory=RealDictCursor
    )

def register_user(user: UserRegister) -> Dict[str, Any]:
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT email FROM users WHERE email = %s", (user.email,))
        if cur.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        hashed_password = pwd_context.hash(user.password)
        full_name = f"{user.firstName} {user.lastName}"  # Объединяем имя и фамилию

        cur.execute("""
            INSERT INTO users (email, password_hash, name)
            VALUES (%s, %s, %s)
            RETURNING id, email, name
        """, (user.email, hashed_password, full_name))

        new_user = cur.fetchone()
        conn.commit()

        logger.info(f"User registered: {user.email}")
        return {
            "status": "success",
            "message": "Registration successful",
            "user": {
                "id": new_user["id"],
                "email": new_user["email"],
                "name": new_user["name"]
            }
        }

    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )
    finally:
        if conn:
            conn.close()

def login_user(user: UserLogin) -> Dict[str, Any]:
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, email, password_hash, name 
            FROM users WHERE email = %s
        """, (user.email,))
        
        db_user = cur.fetchone()

        if not db_user or not pwd_context.verify(user.password, db_user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        token = secrets.token_hex(32)

        cur.execute("""
            UPDATE users SET last_visit = NOW() 
            WHERE id = %s
        """, (db_user["id"],))
        conn.commit()

        return {
            "status": "success",
            "token": token,
            "user": {
                "email": db_user["email"],
                "name": db_user["name"]
            }
        }

    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()