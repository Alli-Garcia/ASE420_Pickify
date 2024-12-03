from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging

# MongoDB URI
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
if not MONGODB_URI:
    raise ValueError("MONGODB_URI is not set in environment variables.")

# Async MongoDB client
client = AsyncIOMotorClient(MONGODB_URI)
database = client["pickify_db"]

# Collections
users_collection = database["users"]
polls_collection = database["polls"]
feedback_collection = database["feedback"]
device_tokens_collection = database["device_tokens"]

async def test_connection():
    """Test MongoDB connection."""
    try:
        await client.admin.command('ping')
        logging.info("MongoDB connected successfully.")
    except Exception as e:
        logging.error(f"MongoDB connection failed: {e}")
