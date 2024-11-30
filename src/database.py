# src/database.py

from motor.motor_asyncio import AsyncIOMotorClient

# MongoDB connection setup
MONGODB_URI = "mongodb://localhost:27017/"
client = AsyncIOMotorClient(MONGODB_URI)
database = client.get_database("pickify_db")
