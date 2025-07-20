from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql+asyncpg://postgres:rombritvin9@127.0.0.1:5432/iipp"

# Создаём асинхронный движок
engine = create_async_engine(DATABASE_URL, echo=True)

# Создаём асинхронную сессию
AsyncSessionLocal = sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
    autoflush=False,
    autocommit=False,
)

Base = declarative_base()

# Асинхронный генератор сессий для FastAPI
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
