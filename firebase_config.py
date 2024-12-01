import os
import firebase_admin
import json
from firebase_admin import credentials

# Load environment variables
firebase_json_content = os.getenv("FIREBASE_ADMIN_JSON_CONTENT")
if not firebase_json_content:
    raise ValueError("Firebase Admin JSON content is missing in environment variables.")

# Parse the JSON content
cred = credentials.Certificate(json.loads(firebase_json_content))

# Initialize Firebase Admin SDK
firebase_admin.initialize_app(cred)
