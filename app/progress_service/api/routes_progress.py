from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime
from .. import models, schemas, db
import requests, jwt
from typing import List

router = APIRouter(tags=["Progress"])

# External service URLs (assuming localhost and given ports)
COURSE_SERVICE_URL = "http://localhost:8002"
ACTIVITY_SERVICE_URL = "http://localhost:8004"

# JWT config for decoding tokens (must match user_service)
SECRET_KEY = "SUPER_SECRET_JWT_KEY"
ALGORITHM = "HS256"

def _get_token_payload(auth_header: str):
    """Decode JWT from Authorization header and return payload."""
    if not auth_header:
        raise HTTPException(status_code=401, detail="Authorization required")
    token = auth_header.replace("Bearer ", "").replace("bearer ", "")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload  # contains user_id and role
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication token")

@router.post("/enroll", response_model=schemas.ProgressOut)
def enroll_course(enroll_req: schemas.EnrollRequest, request: Request, db: Session = Depends(db.get_db)):
    """Enroll the current user in a course."""
    payload = _get_token_payload(request.headers.get("authorization"))
    user_id = payload.get("user_id")
    course_id = enroll_req.course_id
    # Check if already enrolled
    existing = db.query(models.UserCourseEnrollment).filter_by(user_id=user_id, course_id=course_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already enrolled in this course")
    # Verify course exists by calling Course Service (or via DB directly)
    try:
        res = requests.get(f"{COURSE_SERVICE_URL}/courses/{course_id}")
        if res.status_code == 404:
            raise HTTPException(status_code=404, detail="Course not found")
    except requests.RequestException:
        raise HTTPException(status_code=502, detail="Course service unavailable")
    # Enroll user
    enrollment = models.UserCourseEnrollment(user_id=user_id, course_id=course_id, enrolled_at=datetime.utcnow())
    progress = models.UserCourseProgress(user_id=user_id, course_id=course_id, progress_percent=0.00,
                                         last_activity=None, completed_lessons=[], total_time_minutes=0, streak_days=0)
    db.add(enrollment)
    db.add(progress)
    db.commit()
    # Log the action: "Started course '<CourseTitle>'"
    try:
        course_data = res.json()
        course_title = course_data.get("title", str(course_id))
    except ValueError:
        course_title = str(course_id)
    log_message = f"Started course \"{course_title}\""
    # Send log to Activity Service
    log_payload = {"user_id": user_id, "action": log_message, "related_object_type": "course", "related_object_id": course_id}
    try:
        requests.post(f"{ACTIVITY_SERVICE_URL}/activity/logs", json=log_payload)
    except requests.RequestException:
        # If logging fails, we continue without failing enrollment
        pass
    return progress  # returns ProgressOut schema

@router.get("/my-courses", response_model=List[schemas.ProgressOut])
def get_my_courses(request: Request, db: Session = Depends(db.get_db)):
    """Get progress for all courses the current user is enrolled in."""
    payload = _get_token_payload(request.headers.get("authorization"))
    user_id = payload.get("user_id")
    progress_records = db.query(models.UserCourseProgress).filter_by(user_id=user_id).all()
    return progress_records

@router.get("/{course_id}", response_model=schemas.ProgressOut)
def get_course_progress(course_id: int, request: Request, db: Session = Depends(db.get_db)):
    """Get the progress of the current user in a specific course."""
    payload = _get_token_payload(request.headers.get("authorization"))
    user_id = payload.get("user_id")
    progress = db.query(models.UserCourseProgress).filter_by(user_id=user_id, course_id=course_id).first()
    if not progress:
        raise HTTPException(status_code=404, detail="Not enrolled or no progress found for this course")
    return progress

@router.post("/complete-lesson")
def complete_lesson(data: schemas.LessonCompleteRequest, request: Request, db: Session = Depends(db.get_db)):
    """Mark a lesson (content) as completed by the current user."""
    payload = _get_token_payload(request.headers.get("authorization"))
    user_id = payload.get("user_id")
    course_id = data.course_id
    content_id = data.content_id
    # Ensure the user is enrolled in the course
    enrollment = db.query(models.UserCourseEnrollment).filter_by(user_id=user_id, course_id=course_id).first()
    if not enrollment:
        raise HTTPException(status_code=403, detail="User is not enrolled in this course")
    # Verify the content belongs to the course by calling Course Service
    try:
        res = requests.get(f"{COURSE_SERVICE_URL}/content/{content_id}")
        if res.status_code == 404:
            raise HTTPException(status_code=404, detail="Content not found")
        content_info = res.json()
    except requests.RequestException:
        raise HTTPException(status_code=502, detail="Course service unavailable")
    actual_course = content_info.get("course_id")
    if actual_course != course_id:
        raise HTTPException(status_code=400, detail="Content does not belong to the specified course")
    # Check if this lesson was already completed
    existing = db.query(models.LessonCompletion).filter_by(user_id=user_id, content_id=content_id).first()
    if existing:
        # If already completed, we do nothing (could return current progress)
        raise HTTPException(status_code=400, detail="Lesson already marked as completed")
    # Mark lesson as completed
    completion = models.LessonCompletion(user_id=user_id, content_id=content_id, completed_at=datetime.utcnow())
    db.add(completion)
    # Update progress record
    progress = db.query(models.UserCourseProgress).filter_by(user_id=user_id, course_id=course_id).first()
    if not progress:
        # If progress record somehow missing, create it (should not happen if enrolled)
        progress = models.UserCourseProgress(user_id=user_id, course_id=course_id, progress_percent=0.0,
                                             last_activity=None, completed_lessons=[], total_time_minutes=0, streak_days=0)
        db.add(progress)
    # Update completed_lessons array and progress percent
    completed_list = list(progress.completed_lessons) if progress.completed_lessons else []
    completed_list.append(content_id)
    progress.completed_lessons = completed_list
    # Calculate new progress percent = (completed lessons count / total lessons count) * 100
    # Get total number of lessons in this course (via Course Service or DB)
    try:
        # Use Course Service to get total content count for the course
        course_detail = requests.get(f"{COURSE_SERVICE_URL}/courses/{course_id}")
        total_lessons = 0
        if course_detail.status_code == 200:
            course_data = course_detail.json()
            # Count total content items across modules
            modules = course_data.get("modules", [])
            for module in modules:
                total_lessons += len(module.get("content_list", []))
        else:
            # Fallback: direct DB count if course service call fails
            result = db.execute("SELECT COUNT(*) FROM course_content WHERE module_id IN (SELECT id FROM course_modules WHERE course_id=:cid)", {"cid": course_id})
            total_lessons = result.scalar() or 0
    except requests.RequestException:
        # If course service is not reachable, try direct count from DB as fallback
        result = db.execute("SELECT COUNT(*) FROM course_content WHERE module_id IN (SELECT id FROM course_modules WHERE course_id=:cid)", {"cid": course_id})
        total_lessons = result.scalar() or 0
    completed_count = len(completed_list)
    progress.progress_percent = (completed_count / total_lessons * 100) if total_lessons > 0 else 0.0
    progress.last_activity = datetime.utcnow()
    db.commit()
    # Log the progress update action
    slug = content_info.get("course_id")  # We might get slug via another call; if not available, use course_id as identifier
    # Ideally, get course slug or title for the log:
    try:
        course_info = requests.get(f"{COURSE_SERVICE_URL}/courses/{course_id}").json()
        slug = course_info.get("slug", str(course_id))
    except Exception:
        slug = str(course_id)
    log_msg = f"Updated progress in course '{slug}': completed lessons {completed_count}"
    log_payload = {
        "user_id": user_id,
        "action": log_msg,
        "related_object_type": "course_progress",
        "related_object_id": course_id
    }
    try:
        requests.post(f"{ACTIVITY_SERVICE_URL}/activity/logs", json=log_payload)
    except requests.RequestException:
        pass
    return {"detail": "Lesson marked as completed", "progress_percent": float(progress.progress_percent)}

@router.post("/assignments/{assignment_id}/submit")
def submit_assignment(assignment_id: int, data: schemas.AssignmentSubmitRequest, request: Request, db: Session = Depends(db.get_db)):
    """Submit an assignment for the current user."""
    payload = _get_token_payload(request.headers.get("authorization"))
    user_id = payload.get("user_id")
    # Verify assignment exists and get its course_id via Course Service
    try:
        res = requests.get(f"{COURSE_SERVICE_URL}/assignments/{assignment_id}")
        if res.status_code == 404:
            raise HTTPException(status_code=404, detail="Assignment not found")
        assignment_info = res.json()
    except requests.RequestException:
        raise HTTPException(status_code=502, detail="Course service unavailable")
    course_id = assignment_info.get("course_id")
    # Check enrollment in that course
    enrollment = db.query(models.UserCourseEnrollment).filter_by(user_id=user_id, course_id=course_id).first()
    if not enrollment:
        raise HTTPException(status_code=403, detail="User is not enrolled in the course for this assignment")
    # Check if already submitted (one submission per assignment per user)
    existing = db.query(models.UserAssignment).filter_by(user_id=user_id, assignment_id=assignment_id).first()
    if existing:
        # Update existing submission (allow resubmit)
        existing.submission = data.submission
        existing.submitted_at = datetime.utcnow()
        # Reset score and feedback if re-submitting
        existing.score = None
        existing.feedback = None
    else:
        # Create new submission record
        submission = models.UserAssignment(user_id=user_id, assignment_id=assignment_id,
                                          submission=data.submission, submitted_at=datetime.utcnow(),
                                          score=None, feedback=None)
        db.add(submission)
    db.commit()
    # (Optional) Log the submission action
    log_msg = f"Submitted assignment {assignment_id} for course {course_id}"
    log_payload = {
        "user_id": user_id,
        "action": log_msg,
        "related_object_type": "assignment",
        "related_object_id": assignment_id
    }
    try:
        requests.post(f"{ACTIVITY_SERVICE_URL}/activity/logs", json=log_payload)
    except requests.RequestException:
        pass
    return {"detail": "Assignment submitted successfully"}
