from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
import os

MONGODB_URI = os.getenv("MONGODB_URI")
if not MONGODB_URI:
    raise ValueError("MONGODB_URI environment variable is not set.")
# Initialize Async MongoDB Client
client = AsyncIOMotorClient(MONGODB_URI)
database = client["pickify_db"]

polls_collection = database["polls"]
users_collection = database["users"]
device_tokens_collection = database["device_tokens"]

# Test the database connection
async def test_connection():
    try:
        # Use the admin database to ping MongoDB
        admin_db = client["admin"]
        await admin_db.command("ping")
        print("Connected to MongoDB successfully!")
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")