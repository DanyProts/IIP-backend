from fastapi import FastAPI
from .api import routes_activity

app = FastAPI(title="Activity Service")

app.include_router(routes_activity.activity_router, prefix="/activity")
app.include_router(routes_activity.qa_router)  # questions/answers endpoints at root (/questions, /answers)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
