import os
import firebase_admin
from firebase_admin import credentials

# Load environment variables from .env if using python-dotenv
from dotenv import load_dotenv

load_dotenv()

# Get the path to the credentials from an environment variable
firebase_credentials_path = os.getenv("FIREBASE_CREDENTIALS")

# Use the path to initialize the Firebase Admin SDK
if firebase_credentials_path is None:
    raise ValueError("FIREBASE_CREDENTIALS environment variable is not set.")

cred = credentials.Certificate("ASE420_Pickify\config\firebase-adminsdk.json")
firebase_admin.initialize_app(cred)
