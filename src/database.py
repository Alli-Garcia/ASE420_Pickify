# database.py
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
from src.config import MONGODB_URI  # Import from your config, already loaded by dotenv
import logging
import asyncio

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
        raise

async def test_insert():
    logging.debug("Starting test_insert function")
    client = AsyncIOMotorClient("mongodb://127.0.0.1:27017")
    db = client["pickify_db"]
    users = db["users"]

    new_user = {
        "username": "testuser",
        "email": "test@example.com",
        "hashed_password": "hashed_test_password",
        "created_at": datetime.now(timezone.utc)
    }
    logging.debug(f"Inserting new user: {new_user}")

    result = await users.insert_one(new_user)
    logging.debug(f"Insert result: {result.inserted_id}")
    print(f"Inserted user ID: {result.inserted_id}")

asyncio.run(test_insert())