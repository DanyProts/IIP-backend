from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from .. import models, schemas, db
import jwt
from typing import List

# Routers for different endpoint groups
course_router = APIRouter(tags=["Courses"])
content_router = APIRouter(tags=["Content"])
assignments_router = APIRouter(tags=["Assignments"])

# Secret and algorithm should match User Service for JWT decoding
SECRET_KEY = "SUPER_SECRET_JWT_KEY"
ALGORITHM = "HS256"

# Utility: decode JWT and return payload (user_id and role)
def _get_token_payload(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload  # contains user_id and role
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@course_router.get("/", response_model=List[schemas.CourseOut])
def list_courses(db: Session = Depends(db.get_db)):
    """Get a list of all active courses (basic info)."""
    courses = db.query(models.Course).filter(models.Course.is_active == True).all()
    return courses

@course_router.get("/{course_id_or_slug}", response_model=schemas.CourseOut)
def get_course_detail(course_id_or_slug: str, db: Session = Depends(db.get_db)):
    """Get detailed course info by ID or slug, including modules, content, and assignments."""
    # Determine if identifier is numeric (ID) or slug (string)
    course = None
    if course_id_or_slug.isdigit():
        course = db.query(models.Course).filter(models.Course.id == int(course_id_or_slug)).first()
    else:
        course = db.query(models.Course).filter(models.Course.slug == course_id_or_slug).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    # Load modules and content (they will be loaded via relationships because of orm_mode in schema)
    # Optionally, could explicitly join to avoid multiple queries.
    return course

@course_router.post("/", response_model=schemas.CourseOut)
def create_course(course_data: schemas.CourseCreate, request: Request, db: Session = Depends(db.get_db)):
    """Create a new course (admin/instructor only)."""
    # Authenticate and authorize
    auth_header = request.headers.get("authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Authorization token missing")
    token = auth_header.split(" ")[1] if auth_header.startswith("Bearer ") or auth_header.startswith("bearer ") else auth_header
    payload = _get_token_payload(token)
    user_role = payload.get("role")
    user_id = payload.get("user_id")
    if user_role not in ("admin", "instructor"):
        raise HTTPException(status_code=403, detail="Only admins or instructors can create courses")
    # Check slug uniqueness
    exists = db.query(models.Course).filter(models.Course.slug == course_data.slug).first()
    if exists:
        raise HTTPException(status_code=400, detail="Course slug already exists")
    # Create new Course
    new_course = models.Course(
        slug=course_data.slug,
        title=course_data.title,
        description=course_data.description,
        category=course_data.category,
        author_id=user_id,
        level=course_data.level,
        created_at=__import__("datetime").datetime.utcnow(),
        is_active=True,
        duration=course_data.duration
    )
    db.add(new_course)
    db.commit()
    db.refresh(new_course)
    return new_course

@content_router.get("/{content_id}")
def get_content(content_id: int, db: Session = Depends(db.get_db)):
    """Get information about a specific content item (lesson) by ID, including its course."""
    content = db.query(models.CourseContent).join(models.CourseModule).filter(models.CourseContent.id == content_id).first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    # Retrieve course_id and other details
    course_id = content.module.course_id
    result = {
        "id": content.id,
        "title": content.title,
        "content_type": content.content_type,
        "content_url": content.content_url,
        "order_index": content.order_index,
        "duration_minutes": content.duration_minutes,
        "course_id": course_id,
        "module_id": content.module_id,
        "module_title": content.module.title
    }
    return result

@assignments_router.get("/{assignment_id}")
def get_assignment(assignment_id: int, db: Session = Depends(db.get_db)):
    """Get details of a specific assignment by ID (including course_id)."""
    assignment = db.query(models.Assignment).filter(models.Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    result = {
        "id": assignment.id,
        "course_id": assignment.course_id,
        "title": assignment.title,
        "instructions": assignment.instructions,
        "type": assignment.type,
        "max_score": assignment.max_score,
        "deadline": assignment.deadline
    }
    return result
