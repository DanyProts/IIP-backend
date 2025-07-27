from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List
from app.user_service.api.routes_auth import get_current_user 
import json
from app.user_service.models import User as UserModel
from .. import models, schemas, db
from app.subprocess_service.main import run_code_in_sandbox, generate_function_template
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func

router = APIRouter(tags=['Code'])


@router.get("/tasks", response_model=List[schemas.TaskOut])
async def list_tasks(db: AsyncSession = Depends(db.get_db)):
    result = await db.execute(
        select(models.Task).options(selectinload(models.Task.tests)).order_by(models.Task.created_at.desc())
    )
    tasks = result.scalars().all()
    return tasks


@router.get("/tasks/solved", response_model=List[schemas.TaskOut])
async def get_solved_tasks(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(db.get_db)
):
    result = await db.execute(
        select(models.Task)
        .join(models.UserSolvedTask, models.Task.id == models.UserSolvedTask.task_id)
        .where(models.UserSolvedTask.user_id == current_user.id)
        .options(selectinload(models.Task.tests))
        .order_by(models.UserSolvedTask.solved_at.desc())
    )
    tasks = result.scalars().all()
    return tasks


@router.get("/tasks/{task_id}", response_model=schemas.TaskOut)
async def get_task(task_id: int, db: AsyncSession = Depends(db.get_db)):
    result = await db.execute(
        select(models.Task).options(selectinload(models.Task.tests)).filter(models.Task.id == task_id)
    )
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.user_service.api.routes_auth import get_current_user
from app.user_service.models import User as UserModel

@router.post("/tasks/{task_id}/run", response_model=schemas.ExecuteResponse)
async def run_task_code(
    task_id: int,
    code_req: schemas.CodeRunRequest,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(db.get_db)
):
    # Получаем задачу с тестами
    result = await db.execute(
        select(models.Task).options(selectinload(models.Task.tests)).filter(models.Task.id == task_id)
    )
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    func_name = task.function_name
    if not func_name:
        raise HTTPException(status_code=400, detail="Function name not set for this task")

    user_code_body = code_req.code.strip()

    active_tests = [t for t in task.tests if t.is_active]
    if not active_tests:
        raise HTTPException(status_code=400, detail="No active tests for this task")

    first_test_input = active_tests[0].input_data
    try:
        params_dict = json.loads(first_test_input)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON in test input_data")

    params_json = json.dumps(params_dict)

    body = "\n".join("    " + line for line in user_code_body.splitlines())
    full_code = generate_function_template(func_name, params_json).replace("{body}", body)

    results = []
    overall_passed = True
    total_runtime = 0.0
    max_memory = 0.0
    collected_errors = []
    outputs_for_submission = []

    for test in active_tests:
        try:
            input_json_obj = json.loads(test.input_data)
            input_json_str = json.dumps(input_json_obj)

            stdout, stderr, runtime, memory = run_code_in_sandbox(full_code, input_json_str)

            if stderr:
                passed = False
                output = None
                error = stderr
                overall_passed = False
                collected_errors.append(error)
            else:
                try:
                    output = json.loads(stdout)
                except Exception:
                    output = stdout.strip()

                try:
                    expected = json.loads(test.expected_output)
                except Exception:
                    expected = test.expected_output

                passed = (output == expected)
                if not passed:
                    overall_passed = False
                    collected_errors.append(f"Test failed. Expected: {expected}, Got: {output}")

                error = None

            total_runtime += runtime if runtime else 0.0
            if memory and memory > max_memory:
                max_memory = memory

            # Для общего вывода собираем результаты тестов
            outputs_for_submission.append({
                "input": input_json_obj,
                "expected": test.expected_output,
                "output": output,
                "passed": passed,
                "error": error,
                "runtime": runtime,
                "memory": memory,
            })

        except Exception as e:
            passed = False
            output = None
            error = str(e)
            overall_passed = False
            collected_errors.append(error)
            runtime = None
            memory = None

            outputs_for_submission.append({
                "input": test.input_data,
                "expected": test.expected_output,
                "output": None,
                "passed": False,
                "error": error,
                "runtime": runtime,
                "memory": memory,
            })

        results.append(schemas.TestResult(
            input=json.dumps(input_json_obj, ensure_ascii=False),
            expected=test.expected_output,
            output=output,
            passed=passed,
            error=error
        ))

    # Формируем общий статус и вывод для submission
    submission_status = "passed" if overall_passed else "failed"
    submission_output = json.dumps(outputs_for_submission, ensure_ascii=False)
    submission_error = None if overall_passed else "; ".join(collected_errors)

    submission = models.Submission(
        user_id=current_user.id,
        task_id=task_id,
        code=user_code_body,
        language=code_req.language,
        status=submission_status,
        output=submission_output,
        error=submission_error,
        runtime=total_runtime,
        memory=max_memory if max_memory > 0 else None,
    )
    db.add(submission)

    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database commit error: {e}")

    message = "All tests passed" if overall_passed else "Some tests failed"

    # Если все тесты прошли успешно — отмечаем задачу решённой для пользователя
    if overall_passed:
        existing = await db.execute(
            select(models.UserSolvedTask).where(
                (models.UserSolvedTask.user_id == current_user.id) &
                (models.UserSolvedTask.task_id == task_id)
            )
        )
        solved_record = existing.scalars().first()
        if not solved_record:
            solved = models.UserSolvedTask(user_id=current_user.id, task_id=task_id)
            db.add(solved)
            try:
                await db.commit()
            except IntegrityError:
                await db.rollback()

    return schemas.ExecuteResponse(results=results, success=overall_passed, message=message)


@router.get("/tasks/{task_id}/leaderboard")
async def get_task_leaderboard(
    task_id: int,
    db: AsyncSession = Depends(db.get_db)
):
    # Проверяем, что задача существует
    task_res = await db.execute(select(models.Task).filter(models.Task.id == task_id))
    task = task_res.scalars().first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Запрос лучших успешных решений по каждому пользователю:
    # минимальное время и минимальное использование памяти среди успешных
    subq = (
        select(
            models.Submission.user_id,
            func.min(models.Submission.runtime).label("best_runtime"),
            func.min(models.Submission.memory).label("best_memory"),
            func.count(models.Submission.id).label("total_submissions")
        )
        .where(
            (models.Submission.task_id == task_id) &
            (models.Submission.status == "passed")
        )
        .group_by(models.Submission.user_id)
        .subquery()
    )

    # Получаем данные пользователей для отображения имени
    query = (
        select(
            subq.c.user_id,
            subq.c.best_runtime,
            subq.c.best_memory,
            subq.c.total_submissions,
            models.User.name.label("user_name")
        )
        .join(models.User, models.User.id == subq.c.user_id)
        .order_by(subq.c.best_runtime.asc(), subq.c.best_memory.asc())
        .limit(20)
    )

    result = await db.execute(query)
    leaderboard = result.all()

    # Форматируем ответ
    response = [
        {
            "user_id": row.user_id,
            "user_name": row.user_name,
            "best_runtime": row.best_runtime,
            "best_memory": row.best_memory,
            "total_submissions": row.total_submissions,
        }
        for row in leaderboard
    ]

    return {"task_id": task_id, "leaderboard": response}



@router.get("/favorites", response_model=List[schemas.TaskOut])
async def get_favorites(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(db.get_db)
):
    result = await db.execute(
        select(models.Task)
        .join(models.UserFavoriteTask, models.Task.id == models.UserFavoriteTask.task_id)
        .where(models.UserFavoriteTask.user_id == current_user.id)
        .options(selectinload(models.Task.tests))
    )
    tasks = result.scalars().all()
    return tasks


@router.post("/favorites/{task_id}", status_code=status.HTTP_201_CREATED)
async def add_favorite(
    task_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(db.get_db)
):
    task = await db.get(models.Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    fav = models.UserFavoriteTask(user_id=current_user.id, task_id=task_id)
    db.add(fav)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        # Запись уже существует — игнорируем
    return {"detail": "Task added to favorites"}


@router.delete("/favorites/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite(
    task_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(db.get_db)
):
    result = await db.execute(
        select(models.UserFavoriteTask).where(
            (models.UserFavoriteTask.user_id == current_user.id) &
            (models.UserFavoriteTask.task_id == task_id)
        )
    )
    fav = result.scalars().first()
    if not fav:
        raise HTTPException(status_code=404, detail="Favorite not found")

    await db.delete(fav)
    await db.commit()
    return


@router.get("/tasks/{task_id}/solved", response_model=dict)
async def is_task_solved(
    task_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(db.get_db)
):
    result = await db.execute(
        select(models.UserSolvedTask).where(
            (models.UserSolvedTask.user_id == current_user.id) &
            (models.UserSolvedTask.task_id == task_id)
        )
    )
    solved = result.scalars().first()
    return {"solved": solved is not None}
