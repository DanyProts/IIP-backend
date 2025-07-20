from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import routes_gateway

app = FastAPI(title="API Gateway")

origins = [
    "http://localhost:3000",  # фронтенд
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_gateway.router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
