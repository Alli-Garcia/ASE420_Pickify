#config.py
from dotenv import load_dotenv
import os
import logging

# Load environment variables
load_dotenv()

# Get environment variables
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "default_secret_key")
if SECRET_KEY == "default_secret_key":
    logging.warning("JWT_SECRET_KEY is not set. Using a default insecure key!")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

MONGODB_URI = os.getenv("MONGODB_URI", "")
if not MONGODB_URI:
    raise ValueError("MONGODB_URI is not set in the environment variables.")

firebase_json_path = os.getenv("FIREBASE_ADMIN_JSON")
if not firebase_json_path or not os.path.exists(firebase_json_path):
    raise ValueError("Firebase Admin JSON path is missing or invalid.")
