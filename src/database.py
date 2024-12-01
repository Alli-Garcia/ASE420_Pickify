# src/database.py

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from datetime import datetime

# MongoDB connection setup
MONGODB_URI = "mongodb://localhost:27017/"
client = AsyncIOMotorClient(MONGODB_URI)
database = client.get_database("pickify_db")

device_tokens_collection = database["device_tokens"]