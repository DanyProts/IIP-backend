import pytest
from httpx import AsyncClient

BASE_URL = "http://localhost:8000"
TOKEN = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoyMiwicm9sZSI6InN0dWRlbnQiLCJleHAiOjE3NTM1MzQ0OTN9.m_uTjQbhw7LTCuPxgDpr59QCIP1zdr4OzzJ1wAfE0wg"

@pytest.mark.asyncio
async def test_get_favorites():
    async with AsyncClient(base_url=BASE_URL) as client:
        response = await client.get("/favorites", headers={"Authorization": TOKEN})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

@pytest.mark.asyncio
async def test_add_favorite():
    task_id = 1  # Убедитесь, что такая задача существует в базе
    async with AsyncClient(base_url=BASE_URL) as client:
        response = await client.post(f"/favorites/{task_id}", headers={"Authorization": TOKEN})
    assert response.status_code == 201
    assert "Task added to favorites" in response.text

@pytest.mark.asyncio
async def test_remove_favorite():
    task_id = 1  # Убедитесь, что такая задача есть в избранном пользователя
    async with AsyncClient(base_url=BASE_URL) as client:
        response = await client.delete(f"/favorites/{task_id}", headers={"Authorization": TOKEN})
    assert response.status_code == 204
