from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import User, Course, UserCourseEnrollment, UserCourseProgress, UserActivityLog, CourseContent, CourseModule
from app.models.user import UserRegister, UserLogin
from fastapi import HTTPException, status
from passlib.context import CryptContext
from app.models.security import create_access_token, verify_access_token
from sqlalchemy.exc import IntegrityError
from typing import List, Dict, Any
from datetime import datetime

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(select(User).filter(User.email == email))
    return result.scalars().first()


async def register_user(user: UserRegister, session: AsyncSession) -> Dict[str, Any]:
    existing_user = await get_user_by_email(session, user.email)
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    hashed_password = pwd_context.hash(user.password)
    db_user = User(
        email=user.email,
        name=user.name,
        password_hash=hashed_password,
        join_date=datetime.utcnow(),
    )
    session.add(db_user)
    try:
        await session.commit()
        await session.refresh(db_user)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not register user")

    access_token = create_access_token({"sub": db_user.email})

    return {
        "status": "success",
        "message": "Registration successful",
        "token": access_token,
        "user": {
            "id": db_user.id,
            "email": db_user.email,
            "name": db_user.name
        }
    }


async def login_user(user: UserLogin, session: AsyncSession) -> Dict[str, Any]:
    db_user = await get_user_by_email(session, user.email)
    if not db_user or not pwd_context.verify(user.password, db_user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    # Обновляем время последнего визита
    db_user.last_visit = datetime.utcnow()
    await session.commit()

    access_token = create_access_token({"sub": db_user.email})

    return {
        "status": "success",
        "token": access_token,
        "user": {
            "id": db_user.id,
            "email": db_user.email,
            "name": db_user.name
        }
    }


async def get_user_profile(token: str, session: AsyncSession) -> Dict[str, Any]:
    email = verify_access_token(token)
    if email is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    db_user = await get_user_by_email(session, email)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Получаем прогресс пользователя для агрегации статистики
    result_progress = await session.execute(
        select(UserCourseProgress).filter(UserCourseProgress.user_id == db_user.id)
    )
    user_progress_list = result_progress.scalars().all()

    # Получаем курсы, на которые подписан пользователь, вместе с прогрессом
    result = await session.execute(
        select(
            Course, UserCourseProgress
        )
        .join(UserCourseEnrollment, (UserCourseEnrollment.course_id == Course.id))
        .outerjoin(
            UserCourseProgress,
            (UserCourseProgress.course_id == Course.id) & (UserCourseProgress.user_id == db_user.id)
        )
        .filter(UserCourseEnrollment.user_id == db_user.id)
    )
    courses_progress = result.all()

    enrolled_courses = []
    for course, progress in courses_progress:
        completed_lessons = progress.completed_lessons if progress and progress.completed_lessons else []
        enrolled_courses.append({
            "slug": course.slug,
            "progress": float(progress.progress_percent) if progress else 0.0,
            "completedLessons": completed_lessons,
            "lastActivity": progress.last_activity.strftime("%Y-%m-%d") if progress and progress.last_activity else ""
        })

    # Активность пользователя
    result_activity = await session.execute(
        select(UserActivityLog).filter(UserActivityLog.user_id == db_user.id)
    )
    activity_logs = result_activity.scalars().all()

    activity = {}
    for log in activity_logs:
        day = log.timestamp.strftime("%Y-%m-%d")
        if day not in activity:
            activity[day] = {"count": 0, "details": []}
        activity[day]["count"] += 1
        activity[day]["details"].append(log.action)

    # Агрегация статистики из user_progress_list
    total_time = 0
    max_streak = 0
    completed_tasks = 0
    for progress in user_progress_list:
        if progress.total_time_minutes:
            total_time += progress.total_time_minutes
        if progress.streak_days and progress.streak_days > max_streak:
            max_streak = progress.streak_days
        if progress.completed_lessons:
            completed_tasks += len(progress.completed_lessons)

    profile = {
        "id": db_user.id,
        "name": db_user.name,
        "email": db_user.email,
        "joinDate": db_user.join_date.strftime("%d.%m.%Y") if db_user.join_date else "",
        "lastVisit": db_user.last_visit.strftime("%d.%m.%Y %H:%M") if db_user.last_visit else "",
        "stats": {
            "totalTime": f"{total_time} минут",
            "streak": max_streak,
            "completedTasks": completed_tasks
        },
        "enrolledCourses": enrolled_courses,
        "activity": activity,
    }

    return profile


async def update_user_progress(token: str, course_slug: str, completed_lessons: List[int], session: AsyncSession) -> Dict[str, Any]:
    email = verify_access_token(token)
    if email is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    db_user = await get_user_by_email(session, email)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    result_course = await session.execute(select(Course).filter(Course.slug == course_slug))
    db_course = result_course.scalars().first()
    if not db_course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Получаем общее количество уроков через связные таблицы course_modules и course_content
    result_count = await session.execute(
        select(func.count())
        .select_from(CourseContent)
        .join(CourseModule, CourseContent.module_id == CourseModule.id)
        .filter(CourseModule.course_id == db_course.id)
    )
    total_lessons_count = result_count.scalar_one_or_none() or 1

    # Получаем прогресс пользователя для курса
    result_progress = await session.execute(
        select(UserCourseProgress)
        .filter(UserCourseProgress.user_id == db_user.id, UserCourseProgress.course_id == db_course.id)
    )
    user_progress = result_progress.scalars().first()

    progress_percent = round(len(completed_lessons) / total_lessons_count * 100, 2)
    now = datetime.utcnow()

    if not user_progress:
        user_progress = UserCourseProgress(
            user_id=db_user.id,
            course_id=db_course.id,
            progress_percent=progress_percent,
            last_activity=now,
            completed_lessons=completed_lessons
        )
        session.add(user_progress)
    else:
        user_progress.completed_lessons = completed_lessons
        user_progress.progress_percent = progress_percent
        user_progress.last_activity = now

    # Логируем активность пользователя
    activity = UserActivityLog(
        user_id=db_user.id,
        action=f"Обновлен прогресс в курсе '{course_slug}': завершено уроков {len(completed_lessons)}",
        related_object_type="course_progress",
        related_object_id=db_course.id,
        timestamp=now
    )
    session.add(activity)

    await session.commit()

    return {"status": "success", "progress_percent": progress_percent}
