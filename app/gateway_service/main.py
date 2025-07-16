from fastapi import FastAPI
from .api import routes_gateway

app = FastAPI(title="API Gateway")

# ВАЖНО: добавляем префикс "/api" — все маршруты будут /api/...
app.include_router(routes_gateway.router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
