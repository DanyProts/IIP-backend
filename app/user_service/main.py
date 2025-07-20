from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import routes_auth

app = FastAPI(title="User Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # можно ограничить на проде
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_auth.router, prefix="/api/auth")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
