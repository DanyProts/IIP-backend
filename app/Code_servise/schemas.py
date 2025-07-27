from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime

class Test(BaseModel):
    input: str
    expected: str

class TestResult(BaseModel):
    input: str  # JSON-строка с входными данными
    expected: str
    output: Optional[Any]
    passed: bool
    error: Optional[str]

class ExecuteRequest(BaseModel):
    code: str  # тело функции от пользователя (без строки def ...)
    language: str  # например, 'python'

class ExecuteResponse(BaseModel):
    results: List[TestResult]
    success: bool
    message: str

class TaskTestOut(BaseModel):
    id: int
    task_id: int
    input_data: str
    expected_output: str
    is_active: bool
    order_index: int

    class Config:
        orm_mode = True

class TaskOut(BaseModel):
    id: int
    title: str
    description: str
    difficulty: str
    function_name: str
    tests: List[TaskTestOut]

    class Config:
        orm_mode = True

class CodeRunRequest(BaseModel):
    code: str  # тело функции от пользователя (без строки def ...)
    language: str
class SubmissionCreate(BaseModel):
    user_id: int
    task_id: int
    code: str
    language: str
    status: str
    output: Optional[Any] = None
    error: Optional[str] = None
    runtime: Optional[float] = None  # время выполнения в секундах (например)
    memory: Optional[float] = None   # использование памяти в мегабайтах

class SubmissionOut(BaseModel):
    id: int
    user_id: int
    task_id: int
    code: str
    language: str
    status: str
    output: Optional[Any] = None
    error: Optional[str] = None
    runtime: Optional[float] = None
    memory: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True