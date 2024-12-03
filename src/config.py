# config.py
from dotenv import load_dotenv
import os
import logging

# Load environment variables from .env file
load_dotenv()

# Configure logging at the top to ensure any issues are logged properly
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),  # Log to file
        logging.StreamHandler()          # Also log to console
    ]
)

# Retrieve secret key for JWT
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    logging.error("JWT_SECRET_KEY is not set in the environment variables. Using an insecure default key!")
    SECRET_KEY = "default_secret_key"  # Fallback, but insecure. Adjust as needed for production.

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Retrieve MongoDB URI
MONGODB_URI = os.getenv("MONGODB_URI")
if not MONGODB_URI:
    logging.critical("MONGODB_URI is not set in the environment variables. Unable to connect to the database.")
    raise ValueError("MONGODB_URI is not set in the environment variables.")
logging.debug(f"MONGODB_URI: {MONGODB_URI}")
logging.debug(f"SECRET_KEY: {SECRET_KEY}")

# Retrieve Firebase Admin JSON path
firebase_json_path = os.getenv("FIREBASE_ADMIN_JSON")
if not firebase_json_path:
    logging.critical("FIREBASE_ADMIN_JSON path is not set in the environment variables.")
    raise ValueError("Firebase Admin JSON path is missing in the environment variables.")
elif not os.path.exists(firebase_json_path):
    logging.critical(f"Firebase Admin JSON file not found at path: {firebase_json_path}")
    raise ValueError("Firebase Admin JSON path is invalid. File does not exist.")
