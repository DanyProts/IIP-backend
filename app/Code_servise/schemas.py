from pydantic import BaseModel
from typing import List, Optional, Any

# Модель теста
class Test(BaseModel):
    input: str
    expected: Any
    output: Optional[str] = None
    passed: Optional[bool] = None
    error: Optional[str] = None

class TestResult(BaseModel):
    input: dict
    expected: Any
    output: Optional[Any]
    passed: bool
    error: Optional[str]
# Запрос на выполнение кода с тестами
class CodeRunRequest(BaseModel):
    code: str
    language: str

# Запрос к песочнице
class ExecuteRequest(BaseModel):
    code: str
    language: str
    tests: List[Test]

# Ответ от песочницы
class ExecuteResponse(BaseModel):
    results: List[TestResult]
    success: bool
    message: str

# Модели задач и тестов для CRUD
class TaskTestBase(BaseModel):
    input_data: str
    expected_output: str
    is_active: Optional[bool] = True
    order_index: Optional[int] = 0

class TaskTestCreate(TaskTestBase):
    pass

class TaskTestOut(TaskTestBase):
    id: int
    task_id: int

    class Config:
        from_attributes = True  # или orm_mode = True для pydantic v1

class TaskBase(BaseModel):
    title: str
    description: str
    difficulty: Optional[str] = "easy"

class TaskCreate(TaskBase):
    tests: List[TaskTestCreate]

class TaskUpdate(TaskBase):
    tests: Optional[List[TaskTestCreate]] = None

class TaskOut(TaskBase):
    id: int
    tests: List[TaskTestOut] = []

    class Config:
        from_attributes = True  # или orm_mode = True
        
class CodeRunRequest(BaseModel):
    code: str  # функция, которую пишет пользователь
    language: str = "python"
