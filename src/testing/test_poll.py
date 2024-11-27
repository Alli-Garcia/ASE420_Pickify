import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import pytest
from httpx import AsyncClient
from main import app

@pytest.mark.asyncio
async def test_create_poll():
    async with AsyncClient(app=app, base_url="http://127.0.0.1:8000") as ac:
        response = await ac.post("/auth/register", json={
            "username": "polluser",
            "password": "pollpassword",
            "email": "polluser@example.com"
        })
        assert response.status_code == 200

        login_response = await ac.post("/auth/login", data={
            "username": "polluser",
            "password": "pollpassword"
        })
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        poll_response = await ac.post("/polls/create", headers=headers, json={
            "title": "Favorite Fruit",
            "options": ["Apple", "Banana", "Orange"]
        })
        assert poll_response.status_code == 200
