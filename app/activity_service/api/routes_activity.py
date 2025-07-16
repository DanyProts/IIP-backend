from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime
from .. import models, schemas, db
import jwt
from typing import List

activity_router = APIRouter(tags=["Activity Logs"])
qa_router = APIRouter(tags=["Q&A"])

# JWT config to validate tokens
SECRET_KEY = "SUPER_SECRET_JWT_KEY"
ALGORITHM = "HS256"

def _get_user_from_token(auth_header: str):
    if not auth_header:
        raise HTTPException(status_code=401, detail="Authorization required")
    token = auth_header.replace("Bearer ", "").replace("bearer ", "")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {"user_id": payload.get("user_id"), "role": payload.get("role")}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Activity log endpoints
@activity_router.post("/logs", status_code=201)
def create_log(log: dict, db: Session = Depends(db.get_db)):
    """Create a new activity log entry (usually called by other services internally)."""
    # log is expected to be a dict with keys: user_id, action, related_object_type, related_object_id
    try:
        user_id = log["user_id"]
        action = log["action"]
    except KeyError:
        raise HTTPException(status_code=400, detail="Log entry must include user_id and action")
    new_log = models.UserActivityLog(
        user_id=user_id,
        action=action,
        related_object_type=log.get("related_object_type"),
        related_object_id=log.get("related_object_id"),
        timestamp=datetime.utcnow()
    )
    db.add(new_log)
    db.commit()
    db.refresh(new_log)
    return {"detail": "log created"}

@activity_router.get("/logs")
def get_my_logs(request: Request, db: Session = Depends(db.get_db)):
    """Get activity logs for the current user."""
    user_data = _get_user_from_token(request.headers.get("authorization"))
    user_id = user_data["user_id"]
    logs = db.query(models.UserActivityLog).filter(models.UserActivityLog.user_id == user_id).all()
    # Return as list of dicts
    return [
        {
            "id": log.id,
            "action": log.action,
            "related_object_type": log.related_object_type,
            "related_object_id": log.related_object_id,
            "timestamp": log.timestamp
        } for log in logs
    ]

# Q&A endpoints
@qa_router.get("/questions")
def list_questions(course_id: int, db: Session = Depends(db.get_db)):
    """List all questions for a given course_id."""
    questions = db.query(models.Question).filter(models.Question.course_id == course_id).all()
    return questions  # will be returned as list of dicts (can also use schemas.QuestionOut)

@qa_router.get("/questions/{question_id}", response_model=schemas.QuestionDetailOut)
def get_question_detail(question_id: int, db: Session = Depends(db.get_db)):
    """Get a question by ID, including its answers."""
    question = db.query(models.Question).filter(models.Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    # Fetch answers for the question
    answers = db.query(models.Answer).filter(models.Answer.question_id == question_id).all()
    # Attach answers to the question for output
    question_detail = schemas.QuestionDetailOut.from_orm(question)
    question_detail.answers = [schemas.AnswerOut.from_orm(ans) for ans in answers]
    return question_detail

@qa_router.post("/questions", response_model=schemas.QuestionOut, status_code=201)
def post_question(question_data: schemas.QuestionCreate, request: Request, db: Session = Depends(db.get_db)):
    """Post a new question to the forum (requires login, and optionally enrollment in course)."""
    user_data = _get_user_from_token(request.headers.get("authorization"))
    user_id = user_data["user_id"]
    # (Optional) We could verify the user is enrolled in the course by calling Progress Service or checking DB.
    # For simplicity, we'll skip or assume they should be enrolled.
    new_question = models.Question(
        user_id=user_id,
        course_id=question_data.course_id,
        title=question_data.title,
        body=question_data.body,
        created_at=datetime.utcnow()
    )
    db.add(new_question)
    db.commit()
    db.refresh(new_question)
    # Log the question posting
    log_msg = f"Posted question '{question_data.title}' in course {question_data.course_id}"
    db.add(models.UserActivityLog(user_id=user_id, action=log_msg, related_object_type="question", related_object_id=new_question.id, timestamp=datetime.utcnow()))
    db.commit()
    return new_question

@qa_router.post("/questions/{question_id}/answers", response_model=schemas.AnswerOut, status_code=201)
def post_answer(question_id: int, answer_data: schemas.AnswerCreate, request: Request, db: Session = Depends(db.get_db)):
    """Post an answer to a question (requires login)."""
    user_data = _get_user_from_token(request.headers.get("authorization"))
    user_id = user_data["user_id"]
    # Ensure question exists
    question = db.query(models.Question).filter(models.Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    new_answer = models.Answer(
        question_id=question_id,
        user_id=user_id,
        body=answer_data.body,
        created_at=datetime.utcnow(),
        upvotes=0,
        downvotes=0
    )
    db.add(new_answer)
    db.commit()
    db.refresh(new_answer)
    # Log the answer posting
    log_msg = f"Answered question {question_id}"
    db.add(models.UserActivityLog(user_id=user_id, action=log_msg, related_object_type="answer", related_object_id=new_answer.id, timestamp=datetime.utcnow()))
    db.commit()
    return new_answer

@qa_router.post("/answers/{answer_id}/vote")
def vote_answer(answer_id: int, vote: schemas.VoteRequest, request: Request, db: Session = Depends(db.get_db)):
    """Upvote or downvote an answer (requires login)."""
    user_data = _get_user_from_token(request.headers.get("authorization"))
    user_id = user_data["user_id"]
    answer = db.query(models.Answer).filter(models.Answer.id == answer_id).first()
    if not answer:
        raise HTTPException(status_code=404, detail="Answer not found")
    # Check if user already voted on this answer
    existing_vote = db.query(models.Vote).filter(models.Vote.user_id == user_id, models.Vote.answer_id == answer_id).first()
    if existing_vote:
        raise HTTPException(status_code=400, detail="User has already voted on this answer")
    # Record the vote
    vote_type = vote.vote_type.lower()
    if vote_type not in ("up", "down"):
        raise HTTPException(status_code=400, detail="vote_type must be 'up' or 'down'")
    new_vote = models.Vote(user_id=user_id, answer_id=answer_id, vote_type=vote_type)
    # Update answer counts
    if vote_type == "up":
        answer.upvotes += 1
    else:
        answer.downvotes += 1
    db.add(new_vote)
    db.commit()
    # No need to return content except success message
    return {"detail": f"{vote_type}voted answer {answer_id}"}
