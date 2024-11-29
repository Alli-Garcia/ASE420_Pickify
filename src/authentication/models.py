# src/authentication/models.py

from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from bson import ObjectId
from main import database

db: AsyncIOMotorDatabase = database

class User(BaseModel):
    username: str
    email: str
    hashed_password: str

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

# MongoDB collection object for users
users_collection: AsyncIOMotorCollection = db.get_collection("users")
