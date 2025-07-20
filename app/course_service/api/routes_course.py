from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from .. import models, schemas, db
import jwt
from sqlalchemy.orm import selectinload
from typing import List

course_router = APIRouter(tags=["Courses"])
content_router = APIRouter(tags=["Content"])
assignments_router = APIRouter(tags=["Assignments"])

SECRET_KEY = "SUPER_SECRET_JWT_KEY"
ALGORITHM = "HS256"

async def _get_token_payload(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload  # contains user_id and role
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@course_router.get("/", response_model=List[schemas.CourseOut])
async def list_courses(db: AsyncSession = Depends(db.get_db)):
    result = await db.execute(select(models.Course).filter(models.Course.is_active == True))
    courses = result.scalars().all()
    return courses

@course_router.get("/{course_id_or_slug}", response_model=schemas.CourseOut)
async def get_course_detail(course_id_or_slug: str, db: AsyncSession = Depends(db.get_db)):
    course = None
    if course_id_or_slug.isdigit():
        result = await db.execute(select(models.Course).filter(models.Course.id == int(course_id_or_slug)))
        course = result.scalars().first()
    else:
        result = await db.execute(select(models.Course).filter(models.Course.slug == course_id_or_slug))
        course = result.scalars().first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course

@course_router.post("/", response_model=schemas.CourseOut)
async def create_course(course_data: schemas.CourseCreate, request: Request, db: AsyncSession = Depends(db.get_db)):
    auth_header = request.headers.get("authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Authorization token missing")
    token = auth_header.split(" ")[1] if auth_header.lower().startswith("bearer ") else auth_header
    payload = await _get_token_payload(token)
    user_role = payload.get("role")
    user_id = payload.get("user_id")
    if user_role not in ("admin", "instructor"):
        raise HTTPException(status_code=403, detail="Only admins or instructors can create courses")

    result = await db.execute(select(models.Course).filter(models.Course.slug == course_data.slug))
    exists = result.scalars().first()
    if exists:
        raise HTTPException(status_code=400, detail="Course slug already exists")

    import datetime
    new_course = models.Course(
        slug=course_data.slug,
        title=course_data.title,
        description=course_data.description,
        category=course_data.category,
        author_id=user_id,
        level=course_data.level,
        created_at=datetime.datetime.utcnow(),
        is_active=True,
        duration=course_data.duration
    )
    db.add(new_course)
    await db.commit()
    await db.refresh(new_course)
    return new_course

@content_router.get("/{content_id}")
async def get_content(content_id: int, db: AsyncSession = Depends(db.get_db)):
    result = await db.execute(
        select(models.CourseContent)
        .options(selectinload(models.CourseContent.module))
        .filter(models.CourseContent.id == content_id)
    )
    content = result.scalars().first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    if not content.module:
        raise HTTPException(status_code=500, detail="Content module data corrupted or missing")

    course_id = content.module.course_id
    module_title = content.module.title

    return {
        "id": content.id,
        "title": content.title,
        "content_type": content.content_type,
        "content_url": content.content_url,
        "order_index": content.order_index,
        "duration_minutes": content.duration_minutes,
        "course_id": course_id,
        "module_id": content.module_id,
        "module_title": module_title,
    }

@assignments_router.get("/{assignment_id}")
async def get_assignment(assignment_id: int, db: AsyncSession = Depends(db.get_db)):
    result = await db.execute(select(models.Assignment).filter(models.Assignment.id == assignment_id))
    assignment = result.scalars().first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return {
        "id": assignment.id,
        "course_id": assignment.course_id,
        "title": assignment.title,
        "instructions": assignment.instructions,
        "type": assignment.type,
        "max_score": assignment.max_score,
        "deadline": assignment.deadline,
    }
