from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import subprocess
import tempfile
import os

app = FastAPI(title="Sandbox Service")

# Pydantic-схемы, соответствуют schemas в микросервисе Code
class Test(BaseModel):
    input: str
    expected: str

class TestResult(BaseModel):
    input: str
    expected: str
    output: Optional[str]
    passed: bool
    error: Optional[str]

class ExecuteRequest(BaseModel):
    code: str
    language: str  # сейчас поддерживаем только python
    tests: List[Test]

class ExecuteResponse(BaseModel):
    results: List[TestResult]
    success: bool
    message: str


import subprocess
import tempfile
import os

def run_code_in_sandbox(code: str, input_json: str, timeout=5) -> (str, str):
    """
    Запускает python-код в отдельном процессе с передачей input_json в stdin.
    Возвращает (stdout, stderr).
    """
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(code)
        filename = f.name

    try:
        proc = subprocess.run(
            ["python", filename],
            input=input_json.encode(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
        stdout = proc.stdout.decode().strip()
        stderr = proc.stderr.decode().strip()
    except subprocess.TimeoutExpired:
        stdout = ""
        stderr = "Execution timed out"
    finally:
        os.remove(filename)

    return stdout, stderr



@app.post("/execute", response_model=ExecuteResponse)
async def execute_code(request: ExecuteRequest):
    if request.language.lower() != "python":
        raise HTTPException(status_code=400, detail="Only Python language is supported")

    results = []
    for test in request.tests:
        output, error = run_python_code(request.code, test.input)

        passed = (output == test.expected) and (error == "")
        results.append(TestResult(
            input=test.input,
            expected=test.expected,
            output=output,
            passed=passed,
            error=error if error else None
        ))

    success = all(r.passed for r in results)
    message = "All tests passed" if success else "Some tests failed"

    return ExecuteResponse(results=results, success=success, message=message)
