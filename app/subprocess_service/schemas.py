from pydantic import BaseModel
from typing import List, Optional

class Test(BaseModel):
    input: str
    expected: str

class ExecuteRequest(BaseModel):
    code: str
    language: str  # например, "python"
    tests: List[Test]

class TestResult(BaseModel):
    input: str
    expected: str
    output: Optional[str]
    passed: bool
    error: Optional[str]

class ExecuteResponse(BaseModel):
    results: List[TestResult]
    success: bool
    message: str

class CodeRunRequest(BaseModel):
    code: str
    language: str  # например, "python"
