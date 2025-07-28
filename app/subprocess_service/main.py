# sandbox_service.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import subprocess
import tempfile
import os
import json

app = FastAPI(title="Sandbox Service")


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
    language: str  # поддерживаем только python
    tests: List[Test]


class ExecuteResponse(BaseModel):
    results: List[TestResult]
    success: bool
    message: str


def run_code_in_sandbox(code: str, input_json: str, timeout=5) -> (str, str):
    """
    Запускает python-код в отдельном процессе,
    подаёт input_json на stdin,
    возвращает (stdout, stderr)
    """
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding='utf-8') as f:
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


def generate_function_template(func_name: str, args_json: str) -> str:
    try:
        args_dict = json.loads(args_json)
        arg_names = list(args_dict.keys())
    except Exception:
        arg_names = []

    args_str = ", ".join(arg_names)
    template = f"""def {func_name}({args_str}):
{{body}}

import sys
import json

args = json.load(sys.stdin)
result = {func_name}(**args)
print(json.dumps(result))
"""
    return template



@app.post("/execute", response_model=ExecuteResponse)
async def execute_code(request: ExecuteRequest):
    if request.language.lower() != "python":
        raise HTTPException(status_code=400, detail="Only Python language is supported")

    results = []
    for test in request.tests:
        stdout, stderr = run_code_in_sandbox(request.code, test.input)

        if stderr:
            output = None
            passed = False
            error = stderr
        else:
            try:
                output = json.loads(stdout)
            except Exception:
                output = stdout

            try:
                expected = json.loads(test.expected)
            except Exception:
                expected = test.expected

            passed = (output == expected)
            error = None

        results.append(TestResult(
            input=test.input,
            expected=test.expected,
            output=output,
            passed=passed,
            error=error
        ))

    success = all(r.passed for r in results)
    message = "All tests passed" if success else "Some tests failed"

    return ExecuteResponse(results=results, success=success, message=message)
