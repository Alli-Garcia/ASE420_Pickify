# src/authentication/auth_controller.py

from fastapi import APIRouter, HTTPException
from .models import User

router = APIRouter()

# Temporary in-memory user store
user_db = {}

@router.post("/register")
async def register_user(user: User):
    if user.username in user_db:
        raise HTTPException(status_code=400, detail="Username already exists")
    user_db[user.username] = user
    return {"message": "User registered successfully"}

@router.post("/login")
async def login_user(username: str, password: str):
    user = user_db.get(username)
    if not user or user.password != password:
        raise HTTPException(status_code=400, detail="Invalid credentials")
    return {"message": "Login successful"}
