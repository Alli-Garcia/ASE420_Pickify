# src/authentication/models.py

from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from bson import ObjectId
from src.database import database
from typing import Any

# Explicitly mark `db` with `Any` to avoid type checking issues.
db: Any = database  # Using `Any` to silence Pylance type checking issues

class User(BaseModel):
    username: str
    email: str
    hashed_password: str

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

# MongoDB collection object for users
users_collection: Any = db.get_collection("users")  # Again using `Any` to avoid type issues with motor_asyncio

