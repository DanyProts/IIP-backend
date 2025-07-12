import traceback
from fastapi import HTTPException, status
from app.models.user import UserRegister, UserLogin
from passlib.context import CryptContext
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from typing import Dict, Any, List
from app.db.db_config import host, user, db_name, password
import logging

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO)
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
    cur = None
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
        full_name = f"{user.firstName} {user.lastName}"

        cur.execute("""
            INSERT INTO users (email, password_hash, name, join_date)
            VALUES (%s, %s, %s, NOW())
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
        logger.error(f"Registration error: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def login_user(user: UserLogin) -> Dict[str, Any]:
    conn = None
    cur = None
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

        token = db_user["email"]  # Можно заменить на JWT в будущем

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
        logger.error(f"Login error: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def get_user_profile(token: str) -> Dict[str, Any]:
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT * FROM users WHERE email = %s", (token,))
        user = cur.fetchone()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        cur.execute("""
            SELECT c.*, p.progress_percent, p.completed_lessons, p.last_activity
            FROM user_course_enrollment e
            JOIN courses c ON c.id = e.course_id
            LEFT JOIN user_course_progress p ON p.user_id = e.user_id AND p.course_id = e.course_id
            WHERE e.user_id = %s
        """, (user["id"],))
        courses = cur.fetchall()

        cur.execute("""
            SELECT TO_CHAR(timestamp, 'YYYY-MM-DD') as day, action 
            FROM user_activity_log WHERE user_id = %s
        """, (user["id"],))
        rows = cur.fetchall()

        activity = {}
        for row in rows:
            if row["day"] not in activity:
                activity[row["day"]] = {"count": 0, "details": []}
            activity[row["day"]]["count"] += 1
            activity[row["day"]]["details"].append(row["action"])

        enrolled_courses = []
        for c in courses:
            comp_lessons_raw = c.get("completed_lessons")
            if comp_lessons_raw is None:
               comp_lessons_array = []
            else:
               comp_lessons_array = comp_lessons_raw  # psycopg2 преобразует массив в Python list
    
            enrolled_courses.append({
                "slug": c["slug"],
                "progress": float(c.get("progress_percent") or 0),
                "completedLessons": comp_lessons_array,
                "lastActivity": c.get("last_activity").strftime("%Y-%m-%d") if c.get("last_activity") else ""
            })
        return {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "joinDate": user["join_date"].strftime("%d.%m.%Y") if user["join_date"] else "",
            "lastVisit": user["last_visit"].strftime("%d.%m.%Y %H:%M") if user["last_visit"] else "",
            "stats": {
                "totalTime": f"{user.get('total_time_minutes', 0)} минут",
                "streak": user.get("streak_days", 0),
                "completedTasks": user.get("completed_lessons", 0)
            },
            "enrolledCourses": enrolled_courses,
            "activity": activity
        }
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def update_user_progress(token: str, course_slug: str, completed_lessons: List[int]) -> Dict[str, Any]:
    logger.info(f"update_user_progress called with token={token}, course_slug={course_slug}, completed_lessons={completed_lessons}")
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT id FROM users WHERE email = %s", (token,))
        user = cur.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user_id = user["id"]

        cur.execute("SELECT id FROM courses WHERE slug = %s", (course_slug,))
        course = cur.fetchone()
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")
        course_id = course["id"]

        cur.execute("""
            SELECT COUNT(DISTINCT cc.id) AS count 
            FROM course_content cc
            JOIN course_modules cm ON cc.module_id = cm.id
            WHERE cm.course_id = %s
        """, (course_id,))
        module_count = cur.fetchone()["count"]
        if module_count == 0:
            module_count = 1
        progress_percent = round(len(completed_lessons) / module_count * 100, 2)

        cur.execute("""
            INSERT INTO user_course_progress (user_id, course_id, progress_percent, completed_lessons, last_activity)
            VALUES (%s, %s, %s, %s, NOW())
            ON CONFLICT (user_id, course_id) DO UPDATE SET
                progress_percent = EXCLUDED.progress_percent,
                completed_lessons = EXCLUDED.completed_lessons,
                last_activity = EXCLUDED.last_activity
        """, (user_id, course_id, progress_percent, completed_lessons))

        cur.execute("""
            INSERT INTO user_activity_log (user_id, action, related_object_type, related_object_id, timestamp)
            VALUES (%s, %s, %s, %s, NOW())
        """, (
            user_id,
            f"Обновлен прогресс в курсе '{course_slug}': завершено уроков {len(completed_lessons)}",
            "course_progress",
            course_id
        ))

        conn.commit()
        return {"status": "success", "progress_percent": progress_percent}

    except Exception as e:
        logger.error(f"Update progress error: {e}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update progress"
        )
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
