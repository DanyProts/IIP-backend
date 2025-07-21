from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import text
from datetime import datetime
from .. import models, schemas, db
import httpx
import jwt
from typing import List
import traceback
import logging

router = APIRouter(tags=["Progress"])

COURSE_SERVICE_URL = "http://localhost:8002"
ACTIVITY_SERVICE_URL = "http://localhost:8004"

SECRET_KEY = "SUPER_SECRET_JWT_KEY"
ALGORITHM = "HS256"

logger = logging.getLogger("progress_service")
logging.basicConfig(level=logging.INFO)

async def _get_token_payload(auth_header: str):
    if not auth_header:
        logger.warning("Authorization header missing")
        raise HTTPException(status_code=401, detail="Authorization required")
    token = auth_header.replace("Bearer ", "").replace("bearer ", "")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        logger.info(f"Token decoded successfully for user_id={payload.get('user_id')}")
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.PyJWTError as e:
        logger.warning(f"Invalid token: {e}")
        raise HTTPException(status_code=401, detail="Invalid authentication token")

@router.post("/enroll", response_model=schemas.ProgressOut)
async def enroll_course(enroll_req: schemas.EnrollRequest, request: Request, db: AsyncSession = Depends(db.get_db)):
    try:
        payload = await _get_token_payload(request.headers.get("authorization"))
        user_id = payload.get("user_id")
        course_id = enroll_req.course_id
        logger.info(f"User {user_id} enroll request for course {course_id}")

        result = await db.execute(select(models.UserCourseEnrollment).filter_by(user_id=user_id, course_id=course_id))
        existing = result.scalars().first()
        if existing:
            logger.warning(f"User {user_id} already enrolled in course {course_id}")
            raise HTTPException(status_code=400, detail="User already enrolled in this course")

        async with httpx.AsyncClient() as client:
            res = await client.get(f"{COURSE_SERVICE_URL}/courses/{course_id}")
            if res.status_code == 404:
                logger.warning(f"Course {course_id} not found in course service")
                raise HTTPException(status_code=404, detail="Course not found")

        enrollment = models.UserCourseEnrollment(user_id=user_id, course_id=course_id, enrolled_at=datetime.utcnow())
        progress = models.UserCourseProgress(
            user_id=user_id,
            course_id=course_id,
            progress_percent=0.00,
            last_activity=None,
            completed_lessons=[],
            total_time_minutes=0,
            streak_days=0
        )

        db.add(enrollment)
        db.add(progress)
        await db.commit()

        course_title = res.json().get("title", str(course_id))
        logger.info(f"User {user_id} enrolled in course '{course_title}' ({course_id})")

        log_message = f'Started course "{course_title}"'
        log_payload = {
            "user_id": user_id,
            "action": log_message,
            "related_object_type": "course",
            "related_object_id": course_id
        }

        async with httpx.AsyncClient() as client:
            try:
                await client.post(f"{ACTIVITY_SERVICE_URL}/activity/logs", json=log_payload)
                logger.info(f"Activity log created for user {user_id} enrolling course {course_id}")
            except httpx.RequestError as e:
                logger.error(f"Failed to post activity log: {e}")

        return progress

    except Exception as e:
        logger.error(f"Error in enroll_course: {e}")
        traceback.print_exc()
        raise

@router.get("/my-courses", response_model=List[schemas.ProgressOut])
async def get_my_courses(request: Request, db: AsyncSession = Depends(db.get_db)):
    try:
        payload = await _get_token_payload(request.headers.get("authorization"))
        user_id = payload.get("user_id")
        logger.info(f"Fetching courses progress for user {user_id}")
        result = await db.execute(select(models.UserCourseProgress).filter_by(user_id=user_id))
        progress_records = result.scalars().all()
        logger.info(f"Found {len(progress_records)} progress records for user {user_id}")
        return progress_records
    except Exception as e:
        logger.error(f"Error in get_my_courses: {e}")
        traceback.print_exc()
        raise

@router.get("/{course_id}", response_model=schemas.ProgressOut)
async def get_course_progress(course_id: int, request: Request, db: AsyncSession = Depends(db.get_db)):
    try:
        payload = await _get_token_payload(request.headers.get("authorization"))
        user_id = payload.get("user_id")
        logger.info(f"Fetching progress for user {user_id} course {course_id}")
        result = await db.execute(select(models.UserCourseProgress).filter_by(user_id=user_id, course_id=course_id))
        progress = result.scalars().first()
        if not progress:
            logger.warning(f"No progress found for user {user_id} course {course_id}")
            raise HTTPException(status_code=404, detail="Not enrolled or no progress found for this course")
        return progress
    except Exception as e:
        logger.error(f"Error in get_course_progress: {e}")
        traceback.print_exc()
        raise

@router.post("/complete-lesson")
async def complete_lesson(data: schemas.LessonCompleteRequest, request: Request, db: AsyncSession = Depends(db.get_db)):
    logger.info(f"Received complete_lesson request with data: {data}")
    try:
        payload = await _get_token_payload(request.headers.get("authorization"))
        user_id = payload.get("user_id")
        course_id = data.course_id
        content_id = data.content_id

        # Проверка записи пользователя на курс
        result = await db.execute(select(models.UserCourseEnrollment).filter_by(user_id=user_id, course_id=course_id))
        enrollment = result.scalars().first()
        if not enrollment:
            raise HTTPException(status_code=403, detail="User is not enrolled in this course")

        # Проверка урока и курса через микросервис
        async with httpx.AsyncClient() as client:
            res = await client.get(f"{COURSE_SERVICE_URL}/content/{content_id}")
            if res.status_code == 404:
                raise HTTPException(status_code=404, detail="Content not found")
            content_info = res.json()

        if content_info.get("course_id") != course_id:
            raise HTTPException(status_code=400, detail="Content does not belong to the specified course")

        # Проверка, завершён ли урок
        result = await db.execute(select(models.LessonCompletion).filter_by(user_id=user_id, content_id=content_id))
        existing = result.scalars().first()

        if existing:
            # Удаляем старую отметку, чтобы можно было повторно завершить урок
            db.delete(existing)
            await db.flush()  # применяем удаление перед созданием новой записи

        completion = models.LessonCompletion(user_id=user_id, content_id=content_id, completed_at=datetime.utcnow())
        db.add(completion)

        # Обновление прогресса
        result = await db.execute(select(models.UserCourseProgress).filter_by(user_id=user_id, course_id=course_id))
        progress = result.scalars().first()
        if not progress:
            progress = models.UserCourseProgress(
                user_id=user_id,
                course_id=course_id,
                progress_percent=0.0,
                last_activity=None,
                completed_lessons=[],
                total_time_minutes=0,
                streak_days=0
            )
            db.add(progress)

        completed_list = list(progress.completed_lessons) if progress.completed_lessons else []
        if content_id not in completed_list:
            completed_list.append(content_id)
        progress.completed_lessons = completed_list.copy()

        # Подсчёт уроков из базы
        result = await db.execute(
            text("SELECT COUNT(*) FROM course_content WHERE module_id IN (SELECT id FROM course_modules WHERE course_id=:cid)"),
            {"cid": course_id}
        )
        total_lessons = result.scalar() or 0

        completed_count = len(completed_list)
        progress.progress_percent = (completed_count / total_lessons * 100) if total_lessons > 0 else 0.0
        progress.last_activity = datetime.utcnow()

        await db.commit()

        # Лог активности, не критично, пропускаем ошибки
        log_payload = {
            "user_id": user_id,
            "action": f"Updated progress in course {course_id}: completed lessons {completed_count}",
            "related_object_type": "course_progress",
            "related_object_id": course_id
        }
        async with httpx.AsyncClient() as client:
            try:
                await client.post(f"{ACTIVITY_SERVICE_URL}/activity/logs", json=log_payload)
            except Exception:
                pass

        return {"detail": "Lesson marked as completed", "progress_percent": float(progress.progress_percent)}

    except Exception as e:
        logger.error(f"Error in complete_lesson: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/assignments/{assignment_id}/submit")
async def submit_assignment(assignment_id: int, data: schemas.AssignmentSubmitRequest, request: Request, db: AsyncSession = Depends(db.get_db)):
    try:
        payload = await _get_token_payload(request.headers.get("authorization"))
        user_id = payload.get("user_id")
        logger.info(f"User {user_id} submitting assignment {assignment_id}")

        async with httpx.AsyncClient() as client:
            res = await client.get(f"{COURSE_SERVICE_URL}/assignments/{assignment_id}")
            if res.status_code == 404:
                logger.warning(f"Assignment {assignment_id} not found")
                raise HTTPException(status_code=404, detail="Assignment not found")
            assignment_info = res.json()

        course_id = assignment_info.get("course_id")

        result = await db.execute(select(models.UserCourseEnrollment).filter_by(user_id=user_id, course_id=course_id))
        enrollment = result.scalars().first()
        if not enrollment:
            logger.warning(f"User {user_id} is not enrolled in course {course_id} for assignment {assignment_id}")
            raise HTTPException(status_code=403, detail="User is not enrolled in the course for this assignment")

        result = await db.execute(select(models.UserAssignment).filter_by(user_id=user_id, assignment_id=assignment_id))
        existing = result.scalars().first()
        if existing:
            existing.submission = data.submission
            existing.submitted_at = datetime.utcnow()
            existing.score = None
            existing.feedback = None
            logger.info(f"Updated submission for user {user_id} assignment {assignment_id}")
        else:
            submission = models.UserAssignment(
                user_id=user_id,
                assignment_id=assignment_id,
                submission=data.submission,
                submitted_at=datetime.utcnow(),
                score=None,
                feedback=None
            )
            db.add(submission)
            logger.info(f"Created new submission for user {user_id} assignment {assignment_id}")

        await db.commit()

        log_msg = f"Submitted assignment {assignment_id} for course {course_id}"
        log_payload = {
            "user_id": user_id,
            "action": log_msg,
            "related_object_type": "assignment",
            "related_object_id": assignment_id
        }

        async with httpx.AsyncClient() as client:
            try:
                await client.post(f"{ACTIVITY_SERVICE_URL}/activity/logs", json=log_payload)
                logger.info(f"Activity log created for user {user_id} assignment submission")
            except httpx.RequestError as e:
                logger.error(f"Failed to post activity log: {e}")

        return {"detail": "Assignment submitted successfully"}

    except Exception as e:
        logger.error(f"Error in submit_assignment: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/undo-complete-lesson")
async def undo_complete_lesson(data: schemas.LessonCompleteRequest, request: Request, db: AsyncSession = Depends(db.get_db)):
    try:
        payload = await _get_token_payload(request.headers.get("authorization"))
        user_id = payload.get("user_id")
        course_id = data.course_id
        content_id = data.content_id

        # Проверка записи пользователя на курс
        result = await db.execute(select(models.UserCourseEnrollment).filter_by(user_id=user_id, course_id=course_id))
        enrollment = result.scalars().first()
        if not enrollment:
            raise HTTPException(status_code=403, detail="User is not enrolled in this course")

        # Проверка, есть ли отметка о завершении урока
        result = await db.execute(select(models.LessonCompletion).filter_by(user_id=user_id, content_id=content_id))
        completion = result.scalars().first()
        if not completion:
            raise HTTPException(status_code=400, detail="Lesson is not marked as completed")
        logger.info(f"Deleting completion record: {completion}")

        # Удаляем отметку о завершении
        await db.delete(completion)
        await db.flush()  # Применяем удаление в текущей сессии

        # Обновление прогресса
        result = await db.execute(select(models.UserCourseProgress).filter_by(user_id=user_id, course_id=course_id))
        progress = result.scalars().first()
        if not progress:
            raise HTTPException(status_code=404, detail="Progress record not found")

        completed_list = list(progress.completed_lessons) if progress.completed_lessons else []
        if content_id in completed_list:
            completed_list.remove(content_id)
        progress.completed_lessons = completed_list

        # Подсчёт общего количества уроков
        result = await db.execute(
            text("SELECT COUNT(*) FROM course_content WHERE module_id IN (SELECT id FROM course_modules WHERE course_id=:cid)"),
            {"cid": course_id}
        )
        total_lessons = result.scalar() or 0

        completed_count = len(completed_list)
        progress.progress_percent = (completed_count / total_lessons * 100) if total_lessons > 0 else 0.0
        progress.last_activity = datetime.utcnow()

        await db.commit()

        # Лог активности (пропускаем ошибки)
        log_payload = {
            "user_id": user_id,
            "action": f"Removed lesson completion in course {course_id}: lesson {content_id}",
            "related_object_type": "course_progress",
            "related_object_id": course_id
        }
        async with httpx.AsyncClient() as client:
            try:
                await client.post(f"{ACTIVITY_SERVICE_URL}/activity/logs", json=log_payload)
            except Exception:
                pass

        return {"detail": "Lesson marked as not completed", "progress_percent": float(progress.progress_percent)}

    except Exception as e:
        logger.error(f"Error in undo_complete_lesson: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error") 