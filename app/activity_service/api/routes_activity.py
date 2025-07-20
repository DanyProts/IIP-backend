from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime
from .. import models, schemas, db
import jwt
from typing import List

activity_router = APIRouter(tags=["Activity Logs"])
qa_router = APIRouter(tags=["Q&A"])

SECRET_KEY = "SUPER_SECRET_JWT_KEY"
ALGORITHM = "HS256"

async def _get_user_from_token(auth_header: str):
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
async def create_log(log: dict, db: AsyncSession = Depends(db.get_db)):
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
    await db.commit()
    await db.refresh(new_log)
    return {"detail": "log created"}

@activity_router.get("/logs")
async def get_my_logs(request: Request, db: AsyncSession = Depends(db.get_db)):
    user_data = await _get_user_from_token(request.headers.get("authorization"))
    user_id = user_data["user_id"]

    result = await db.execute(select(models.UserActivityLog).filter(models.UserActivityLog.user_id == user_id))
    logs = result.scalars().all()

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
async def list_questions(course_id: int, db: AsyncSession = Depends(db.get_db)):
    result = await db.execute(select(models.Question).filter(models.Question.course_id == course_id))
    questions = result.scalars().all()
    return questions

@qa_router.get("/questions/{question_id}", response_model=schemas.QuestionDetailOut)
async def get_question_detail(question_id: int, db: AsyncSession = Depends(db.get_db)):
    result = await db.execute(select(models.Question).filter(models.Question.id == question_id))
    question = result.scalars().first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    result_ans = await db.execute(select(models.Answer).filter(models.Answer.question_id == question_id))
    answers = result_ans.scalars().all()

    question_detail = schemas.QuestionDetailOut.from_orm(question)
    question_detail.answers = [schemas.AnswerOut.from_orm(ans) for ans in answers]
    return question_detail

@qa_router.post("/questions", response_model=schemas.QuestionOut, status_code=201)
async def post_question(question_data: schemas.QuestionCreate, request: Request, db: AsyncSession = Depends(db.get_db)):
    user_data = await _get_user_from_token(request.headers.get("authorization"))
    user_id = user_data["user_id"]

    new_question = models.Question(
        user_id=user_id,
        course_id=question_data.course_id,
        title=question_data.title,
        body=question_data.body,
        created_at=datetime.utcnow()
    )
    db.add(new_question)
    await db.commit()
    await db.refresh(new_question)

    log_msg = f"Posted question '{question_data.title}' in course {question_data.course_id}"
    db.add(models.UserActivityLog(
        user_id=user_id,
        action=log_msg,
        related_object_type="question",
        related_object_id=new_question.id,
        timestamp=datetime.utcnow()
    ))
    await db.commit()

    return new_question

@qa_router.post("/questions/{question_id}/answers", response_model=schemas.AnswerOut, status_code=201)
async def post_answer(question_id: int, answer_data: schemas.AnswerCreate, request: Request, db: AsyncSession = Depends(db.get_db)):
    user_data = await _get_user_from_token(request.headers.get("authorization"))
    user_id = user_data["user_id"]

    result = await db.execute(select(models.Question).filter(models.Question.id == question_id))
    question = result.scalars().first()
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
    await db.commit()
    await db.refresh(new_answer)

    log_msg = f"Answered question {question_id}"
    db.add(models.UserActivityLog(
        user_id=user_id,
        action=log_msg,
        related_object_type="answer",
        related_object_id=new_answer.id,
        timestamp=datetime.utcnow()
    ))
    await db.commit()

    return new_answer

@qa_router.post("/answers/{answer_id}/vote")
async def vote_answer(answer_id: int, vote: schemas.VoteRequest, request: Request, db: AsyncSession = Depends(db.get_db)):
    user_data = await _get_user_from_token(request.headers.get("authorization"))
    user_id = user_data["user_id"]

    result = await db.execute(select(models.Answer).filter(models.Answer.id == answer_id))
    answer = result.scalars().first()
    if not answer:
        raise HTTPException(status_code=404, detail="Answer not found")

    result_vote = await db.execute(select(models.Vote).filter(models.Vote.user_id == user_id, models.Vote.answer_id == answer_id))
    existing_vote = result_vote.scalars().first()
    if existing_vote:
        raise HTTPException(status_code=400, detail="User has already voted on this answer")

    vote_type = vote.vote_type.lower()
    if vote_type not in ("up", "down"):
        raise HTTPException(status_code=400, detail="vote_type must be 'up' or 'down'")

    new_vote = models.Vote(user_id=user_id, answer_id=answer_id, vote_type=vote_type)
    if vote_type == "up":
        answer.upvotes += 1
    else:
        answer.downvotes += 1

    db.add(new_vote)
    await db.commit()

    return {"detail": f"{vote_type}voted answer {answer_id}"}
