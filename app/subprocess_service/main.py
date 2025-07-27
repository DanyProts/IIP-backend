# sandbox_service.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import subprocess
import tempfile
import os
import json
import time
import psutil  # pip install psutil

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
    runtime: Optional[float]  # время в секундах
    memory: Optional[float]   # память в мегабайтах


class ExecuteRequest(BaseModel):
    code: str
    language: str  # поддерживаем только python
    tests: List[Test]


class ExecuteResponse(BaseModel):
    results: List[TestResult]
    success: bool
    message: str


def run_code_in_sandbox(code: str, input_json: str, timeout=5) -> (str, str, float, float):
    """
    Запускает python-код в отдельном процессе,
    подаёт input_json на stdin,
    возвращает (stdout, stderr, runtime_seconds, memory_megabytes)
    """
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding='utf-8') as f:
        f.write(code)
        filename = f.name

    try:
        start_time = time.time()

        proc = subprocess.Popen(
            ["python", filename],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        try:
            # До communicate попробуем получить psutil.Process
            p = psutil.Process(proc.pid)
        except Exception:
            p = None

        try:
            stdout_bytes, stderr_bytes = proc.communicate(input=input_json.encode(), timeout=timeout)
            returncode = proc.returncode
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout_bytes, stderr_bytes = proc.communicate()
            returncode = proc.returncode
            stderr = "Execution timed out"
            return "", stderr, timeout, None

        end_time = time.time()
        runtime = end_time - start_time

        # Получаем пиковое использование памяти, если процесс ещё доступен
        memory = None
        if p is not None:
            try:
                # p.memory_info().rss - текущая память, пиковое - p.memory_info().peak_wset (Windows) или p.memory_info().peak_rss (Linux)
                if hasattr(p.memory_info(), 'peak_wset'):  # Windows
                    memory = p.memory_info().peak_wset / (1024 * 1024)
                elif hasattr(p.memory_info(), 'rss'):  # Linux
                    memory = p.memory_info().rss / (1024 * 1024)
                else:
                    memory = None
            except Exception:
                memory = None

        stdout = stdout_bytes.decode().strip()
        stderr = stderr_bytes.decode().strip()

    finally:
        if os.path.exists(filename):
            os.remove(filename)

    return stdout, stderr, runtime, memory


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
        stdout, stderr, runtime, memory = run_code_in_sandbox(request.code, test.input)

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
            error=error,
            runtime=runtime,
            memory=memory
        ))

    success = all(r.passed for r in results)
    message = "All tests passed" if success else "Some tests failed"

    return ExecuteResponse(results=results, success=success, message=message)
