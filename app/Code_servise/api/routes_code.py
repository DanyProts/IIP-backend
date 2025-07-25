from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List
import json

from .. import models, schemas, db
from app.subprocess_service.main import run_code_in_sandbox, generate_function_template

router = APIRouter(tags=['Code'])


@router.get("/tasks", response_model=List[schemas.TaskOut])
async def list_tasks(db: AsyncSession = Depends(db.get_db)):
    result = await db.execute(
        select(models.Task).options(selectinload(models.Task.tests)).order_by(models.Task.created_at.desc())
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


@router.post("/tasks/{task_id}/run", response_model=schemas.ExecuteResponse)
async def run_task_code(task_id: int, code_req: schemas.CodeRunRequest, db: AsyncSession = Depends(db.get_db)):
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

    # Активные тесты
    active_tests = [t for t in task.tests if t.is_active]
    if not active_tests:
        raise HTTPException(status_code=400, detail="No active tests for this task")

    first_test_input = active_tests[0].input_data
    try:
        params_dict = json.loads(first_test_input)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON in test input_data")

    params_json = json.dumps(params_dict)

    # Формируем тело с отступами 4 пробела
    body = "\n".join("    " + line for line in user_code_body.splitlines())

    # Генерируем полный код с шаблоном
    full_code = generate_function_template(func_name, params_json).replace("{body}", body)

    results = []

    for test in active_tests:
        try:
            input_json_obj = json.loads(test.input_data)
            input_json_str = json.dumps(input_json_obj)

            stdout, stderr = run_code_in_sandbox(full_code, input_json_str)

            if stderr:
                passed = False
                output = None
                error = stderr
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
                error = None

        except Exception as e:
            passed = False
            output = None
            error = str(e)

        results.append(schemas.TestResult(
            input=json.dumps(input_json_obj, ensure_ascii=False),  # Строка JSON, чтобы соответствовать pydantic
            expected=test.expected_output,
            output=output,
            passed=passed,
            error=error
        ))

    success = all(r.passed for r in results)
    message = "All tests passed" if success else "Some tests failed"

    return schemas.ExecuteResponse(results=results, success=success, message=message)
