from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import routes_auth

app = FastAPI(title="User Service")

# CORS — если фронт делает запросы
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # можно указать конкретный фронт
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# подключаем маршруты с /api/auth
app.include_router(routes_auth.router, prefix="/api/auth")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
