from fastapi import APIRouter, Request, HTTPException, Response
import httpx

router = APIRouter()

USER_SERVICE_URL = "http://localhost:8001"
COURSE_SERVICE_URL = "http://localhost:8002"
PROGRESS_SERVICE_URL = "http://localhost:8003"
ACTIVITY_SERVICE_URL = "http://localhost:8004"
SUBPROCESS_SERVICE_URL ="http://localhost:8005"
CODE_SERVICE_URL = "http://localhost:8006"



async def _forward_async(method: str, url: str, request: Request) -> Response:
    headers = {}
    auth_header = request.headers.get("authorization")
    if auth_header:
        headers["authorization"] = auth_header

    try:
        async with httpx.AsyncClient() as client:
            if method == "GET":
                resp = await client.get(url, headers=headers, params=request.query_params)
            elif method == "POST":
                try:
                    body = await request.json()
                except Exception:
                    body = None
                resp = await client.post(url, headers=headers, json=body)
            elif method == "PUT":
                try:
                    body = await request.json()
                except Exception:
                    body = None
                resp = await client.put(url, headers=headers, json=body)
            elif method == "DELETE":
                resp = await client.delete(url, headers=headers, params=request.query_params)
            else:
                try:
                    body = await request.json()
                except Exception:
                    body = None
                resp = await client.request(method, url, headers=headers, json=body, params=request.query_params)
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Microservice unreachable: {str(e)}")

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type=resp.headers.get("content-type", "application/json")
    )

# === Auth ===
@router.post("/auth/login")
async def login_route(request: Request):
    return await _forward_async("POST", f"{USER_SERVICE_URL}/api/auth/login", request)

@router.post("/auth/register")
async def register_route(request: Request):
    return await _forward_async("POST", f"{USER_SERVICE_URL}/api/auth/register", request)

@router.get("/auth/users/me")
async def me_route(request: Request):
    return await _forward_async("GET", f"{USER_SERVICE_URL}/api/auth/users/me", request)

# ==== Courses ====
@router.get("/courses")
async def list_courses(request: Request):
    return await _forward_async("GET", f"{COURSE_SERVICE_URL}/api/courses", request)

@router.get("/courses/{course_id}")
async def get_course(course_id: str, request: Request):
    return await _forward_async("GET", f"{COURSE_SERVICE_URL}/api/courses/{course_id}", request)

@router.post("/courses")
async def create_course(request: Request):
    return await _forward_async("POST", f"{COURSE_SERVICE_URL}/api/courses", request)

# ==== Progress ====
@router.post("/progress/enroll")
async def enroll_course(request: Request):
    return await _forward_async("POST", f"{PROGRESS_SERVICE_URL}/api/progress/enroll", request)

@router.get("/progress/my-courses")
async def my_courses(request: Request):
    return await _forward_async("GET", f"{PROGRESS_SERVICE_URL}/api/progress/my-courses", request)

@router.post("/progress/complete-lesson")
async def complete_lesson(request: Request):
    return await _forward_async("POST", f"{PROGRESS_SERVICE_URL}/api/progress/complete-lesson", request)

@router.post("/progress/update")
async def update_progress(request: Request):
    return await _forward_async("POST", f"{PROGRESS_SERVICE_URL}/api/progress/update", request)

# ==== Activity ====
@router.get("/questions")
async def get_questions(request: Request):
    return await _forward_async("GET", f"{ACTIVITY_SERVICE_URL}/api/questions", request)

@router.get("/questions/{question_id}")
async def get_question(question_id: int, request: Request):
    return await _forward_async("GET", f"{ACTIVITY_SERVICE_URL}/api/questions/{question_id}", request)

@router.post("/questions")
async def post_question(request: Request):
    return await _forward_async("POST", f"{ACTIVITY_SERVICE_URL}/api/questions", request)

@router.post("/questions/{question_id}/answers")
async def answer_question(question_id: int, request: Request):
    return await _forward_async("POST", f"{ACTIVITY_SERVICE_URL}/api/questions/{question_id}/answers", request)

@router.post("/answers/{answer_id}/vote")
async def vote_answer(answer_id: int, request: Request):
    return await _forward_async("POST", f"{ACTIVITY_SERVICE_URL}/api/answers/{answer_id}/vote", request)

@router.get("/activity/logs")
async def get_logs(request: Request):
    return await _forward_async("GET", f"{ACTIVITY_SERVICE_URL}/activity/logs", request)

@router.post("/activity/logs")
async def create_log(request: Request):
    return await _forward_async("POST", f"{ACTIVITY_SERVICE_URL}/activity/logs", request)

@router.post("/assignments/{assignment_id}/submit")
async def submit_assignment(assignment_id: int, request: Request):
    return await _forward_async("POST", f"{PROGRESS_SERVICE_URL}/api/progress/assignments/{assignment_id}/submit", request)

@router.post("/progress/undo-complete-lesson")
async def undo_complete_lesson(request: Request):
    return await _forward_async("POST", f"{PROGRESS_SERVICE_URL}/api/progress/undo-complete-lesson", request)

@router.get("/activity/streak")
async def get_streak(request: Request):
    return await _forward_async("GET", f"{ACTIVITY_SERVICE_URL}/activity/streak", request)

@router.get("/activity/tasks/completed-count")
async def proxy_completed_tasks_count(request: Request):
    return await _forward_async("GET", f"{ACTIVITY_SERVICE_URL}/activity/tasks/completed-count", request)

@router.get("/progress/task/completed-count")
async def test_completed_count(request: Request):
    auth = request.headers.get("authorization")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{PROGRESS_SERVICE_URL}/api/progress/task/completed-count",
                headers={"authorization": auth} if auth else None,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))



@router.post("/progress/enroll")
async def proxy_enroll_course(request: Request):
    # Проксируем запрос в progress_service /enroll
    async with httpx.AsyncClient() as client:
        headers = {"authorization": request.headers.get("authorization")}
        body = await request.json()
        try:
            response = await client.post(f"{PROGRESS_SERVICE_URL}/enroll", json=body, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        
@router.post("/auth/verify-email")
async def verify_email(request: Request):
    async with httpx.AsyncClient() as client:
        headers = {"authorization": request.headers.get("authorization")} if request.headers.get("authorization") else {}
        body = await request.json()
        try:
            response = await client.post(f"{USER_SERVICE_URL}/api/auth/verify-email", json=body, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


@router.get("/tasks")
async def list_tasks(request: Request):
    return await _forward_async("GET", f"{CODE_SERVICE_URL}/api/code/tasks", request)

@router.get("/tasks/solved")
async def get_solved_tasks(request: Request):
    print("Proxy: /tasks/solved called")
    return await _forward_async("GET", f"{CODE_SERVICE_URL}/api/code/tasks/solved", request)

@router.get("/tasks/{task_id}/solved")
async def is_task_solved(task_id: int, request: Request):
    return await _forward_async("GET", f"{CODE_SERVICE_URL}/api/code/tasks/{task_id}/solved", request)

@router.get("/tasks/{task_id}")
async def get_task(task_id: int, request: Request):
    print(f"Proxy: /tasks/{task_id} called")
    return await _forward_async("GET", f"{CODE_SERVICE_URL}/api/code/tasks/{task_id}", request)

@router.post("/tasks/{task_id}/run")
async def run_task_code(task_id: int, request: Request):
    return await _forward_async("POST", f"{CODE_SERVICE_URL}/api/code/tasks/{task_id}/run", request)

@router.get("/tasks/{task_id}/leaderboard")
async def get_task_leaderboard(task_id: int, request: Request):
    target_url = f"{CODE_SERVICE_URL}/api/code/tasks/{task_id}/leaderboard"
    return await _forward_async("GET", target_url, request)

@router.get("/favorites")
async def get_favorites(request: Request):
    return await _forward_async("GET", f"{CODE_SERVICE_URL}/api/code/favorites", request)

@router.post("/favorites/{task_id}")
async def add_favorite(task_id: int, request: Request):
    return await _forward_async("POST", f"{CODE_SERVICE_URL}/api/code/favorites/{task_id}", request)

@router.delete("/favorites/{task_id}")
async def remove_favorite(task_id: int, request: Request):
    return await _forward_async("DELETE", f"{CODE_SERVICE_URL}/api/code/favorites/{task_id}", request)
