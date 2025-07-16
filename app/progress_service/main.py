from fastapi import FastAPI
from .api import routes_progress

app = FastAPI(title="Progress Service")

app.include_router(routes_progress.router, prefix="/progress")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
