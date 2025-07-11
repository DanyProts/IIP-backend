from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import setup_logging, get_cors_settings
from app.api import routes_auth



setup_logging()

app = FastAPI()

# CORS
cors_config = get_cors_settings()
app.add_middleware(CORSMiddleware, **cors_config)

# Роуты
app.include_router(routes_auth.router, prefix="/api/auth")


@app.get("/api/test")
async def test():
    return {"message": "API is working!"}
