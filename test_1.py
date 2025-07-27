import requests

BASE_URL = "http://localhost:8006/api/code"
TASK_ID = 1  # Пример задачи Two Sum

# Тело функции, которое пишет пользователь (без def и заголовка)
user_code_body = """
index = []
for i in range(len(nums)-1):
    for j in range(i+1, len(nums)):
        if nums[i]+nums[j] == target:
            index.append(i)
            index.append(j)
return index
"""

def run_code_on_task(task_id: int, code_body: str):
    url = f"{BASE_URL}/tasks/{task_id}/run"
    payload = {
        "code": code_body,
        "language": "python"
    }
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()

if __name__ == "__main__":
    result = run_code_on_task(TASK_ID, user_code_body)
    print(f"Success: {result['success']}")
    print(f"Message: {result['message']}")
    print("Test results:")
    for r in result["results"]:
        print(f"Input: {r['input']}")
        print(f"Expected: {r['expected']}")
        print(f"Output: {r['output']}")
        print(f"Passed: {r['passed']}")
        if r.get("error"):
            print(f"Error: {r['error']}")
        print("---")
