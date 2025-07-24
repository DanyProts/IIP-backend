from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List
import httpx
import json
from .. import models, schemas, db
from app.subprocess_service.main import run_code_in_sandbox
from test import wrap_user_function
router = APIRouter(tags=['Code'])

SANDBOX_URL = "http://localhost:8005"  # URL вашего SandBox микросервиса


# Получить список всех задач с тестами
@router.get("/tasks", response_model=List[schemas.TaskOut])
async def list_tasks(db: AsyncSession = Depends(db.get_db)):
    result = await db.execute(
        select(models.Task).options(selectinload(models.Task.tests)).order_by(models.Task.created_at.desc())
    )
    tasks = result.scalars().all()
    return tasks


# Получить задачу по id с тестами
@router.get("/tasks/{task_id}", response_model=schemas.TaskOut)
async def get_task(task_id: int, db: AsyncSession = Depends(db.get_db)):
    result = await db.execute(
        select(models.Task).options(selectinload(models.Task.tests)).filter(models.Task.id == task_id)
    )
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


# Создать задачу с тестами
@router.post("/tasks", response_model=schemas.TaskOut, status_code=status.HTTP_201_CREATED)
async def create_task(task_data: schemas.TaskCreate, db: AsyncSession = Depends(db.get_db)):
    new_task = models.Task(
        title=task_data.title,
        description=task_data.description,
        difficulty=task_data.difficulty
    )
    db.add(new_task)
    await db.flush()  # чтобы получить id до коммита

    for idx, test_data in enumerate(task_data.tests):
        test = models.TaskTest(
            task_id=new_task.id,
            input_data=test_data.input_data,
            expected_output=test_data.expected_output,
            is_active=test_data.is_active if test_data.is_active is not None else True,
            order_index=idx
        )
        db.add(test)

    await db.commit()
    await db.refresh(new_task)
    return new_task


# Запуск кода пользователя с тестами через SandBox
@router.post("/tasks/{task_id}/run", response_model=schemas.ExecuteResponse)
async def run_task_code(task_id: int, code_req: schemas.CodeRunRequest, db: AsyncSession = Depends(db.get_db)):
    # Получаем задачу и тесты
    result = await db.execute(
        select(models.Task).options(selectinload(models.Task.tests)).filter(models.Task.id == task_id)
    )
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    func_name = task.function_name  # поле function_name в таблице tasks
    user_code = code_req.code.strip()

    if not user_code.startswith("def " + func_name):
        raise HTTPException(status_code=400, detail=f"Function name must be '{func_name}'")

    full_code = wrap_user_function(user_code, func_name)

    active_tests = [t for t in task.tests if t.is_active]
    if not active_tests:
        raise HTTPException(status_code=400, detail="No active tests for this task")

    results = []
    for test in active_tests:
        try:
            input_json = test.input_data
            # Убедимся, что input_data - это JSON строка с именованными параметрами
            # Если хранится как строка, конвертируем
            if isinstance(input_json, str):
                input_json_obj = json.loads(input_json)
            else:
                input_json_obj = input_json

            input_json_str = json.dumps(input_json_obj)

            stdout, stderr = run_code_in_sandbox(full_code, input_json_str)

            if stderr:
                passed = False
                output = None
                error = stderr
            else:
                # Сравниваем ожидаемый вывод и результат (по JSON)
                output = json.loads(stdout)
                try:
                    expected = json.loads(test.expected_output)
                except Exception:
                    expected = test.expected_output  # если не JSON, сравниваем как есть

                passed = (output == expected)
                error = None

        except Exception as e:
            passed = False
            output = None
            error = str(e)

        results.append(schemas.TestResult(
            input=input_json_obj,
            expected=test.expected_output,
            output=output,
            passed=passed,
            error=error
        ))

    success = all(r.passed for r in results)
    message = "All tests passed" if success else "Some tests failed"

    return schemas.ExecuteResponse(results=results, success=success, message=message)   