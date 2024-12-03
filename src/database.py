# database.py
from motor.motor_asyncio import AsyncIOMotorClient
from src.config import MONGODB_URI  # Import from your config, already loaded by dotenv
import logging

# Async MongoDB client
client = AsyncIOMotorClient(MONGODB_URI)
database = client.get_database("pickify_db")  # Make sure this database name matches your URI

# Collections
users_collection = database.get_collection("users")
polls_collection = database.get_collection("polls")
feedback_collection = database.get_collection("feedback")
device_tokens_collection = database.get_collection("device_tokens")

async def test_connection():
    """Test MongoDB connection."""
    try:
        await client.admin.command('ping')
        logging.info("MongoDB connected successfully.")
    except Exception as e:
        logging.error(f"MongoDB connection failed: {e}", exc_info=True)
