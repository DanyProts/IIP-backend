from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import routes_code  # ваш файл с роутерами, путь скорректируйте по структуре
app = FastAPI(title="Code Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # на проде лучше ограничить домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_code.router, prefix="/api/code")
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8006, reload=True)
