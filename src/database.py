from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
import os

# MongoDB connection setup
MONGODB_USERNAME = os.getenv("MONGODB_USERNAME")  # Username environment variable
MONGODB_PASSWORD = os.getenv("MONGODB_PASSWORD")  # Password environment variable

if not MONGODB_USERNAME or not MONGODB_PASSWORD:
    raise ValueError("MONGODB_USERNAME or MONGODB_PASSWORD environment variables are not set.")

MONGODB_URI = f"mongodb+srv://{MONGODB_USERNAME}:{MONGODB_PASSWORD}@pickify.1ozxp.mongodb.net/?retryWrites=true&w=majority&appName=Pickify"

# Initialize Async MongoDB Client
client = AsyncIOMotorClient(MONGODB_URI)
database = client["pickify_db"]

polls_collection = database["polls"]
users_collection = database["users"]
device_tokens_collection = database["device_tokens"]

# Test the database connection
async def test_connection():
    try:
        # Ping the database to check connection
        await database.command("ping")
        print("Connected to MongoDB successfully!")
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")