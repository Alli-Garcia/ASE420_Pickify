from fastapi import APIRouter, Depends, HTTPException, Form, BackgroundTasks, Request
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt
from src.authentication.auth_controller import get_current_user
from src.notifications.fcm_manager import send_feedback_notification
from src.database import database
from src.config import SECRET_KEY, ALGORITHM
from bson import ObjectId
from typing import List
from datetime import datetime
from .models import Feedback  # Import Feedback from models.py
import logging
from pydantic import BaseModel, ValidationError

router = APIRouter()

# Utility function to serialize MongoDB documents
def serialize_document(doc):
    if isinstance(doc, dict):
        return {key: serialize_document(value) for key, value in doc.items()}
    elif isinstance(doc, list):
        return [serialize_document(item) for item in doc]
    elif isinstance(doc, ObjectId):
        return str(doc)
    return doc

# Collections
feedback_collection = database.get_collection("feedback")
polls_collection = database.get_collection("polls")


# Add Feedback
@router.post("/add")
async def add_feedback(
    request: Request,
    background_tasks: BackgroundTasks,
    poll_id: str = Form(...),
    comment: str = Form(...),
):
    try:
        logging.info(f"Attempting to add feedback for poll {poll_id}")
        if not is_valid_objectid(poll_id):
            logging.error(f"Invalid poll_id: {poll_id}")
            raise HTTPException(status_code=400, detail="Invalid poll ID format")

        # Retrieve the poll
        poll = await polls_collection.find_one({"_id": ObjectId(poll_id)})
        if not poll:
            logging.error(f"Poll {poll_id} not found.")
            raise HTTPException(status_code=404, detail="Poll not found")

        # Authorization
        guest_email = request.query_params.get("email")
        current_user = None
        token = request.cookies.get("Authorization")
        if token:
            try:
                scheme, token_value = token.split(" ", 1)
                if scheme.lower() == "bearer":
                    payload = jwt.decode(token_value, SECRET_KEY, algorithms=[ALGORITHM])
                    current_user = payload.get("sub")
            except (JWTError, ValueError):
                logging.warning("Failed to decode token. Treating as guest.")

        commenter = current_user or guest_email or "Anonymous"
        # Prepare feedback data
        feedback_data = {
            "poll_id": str(poll_id),
            "comment": comment,
            "commenter": commenter,
            "created_at": datetime.now()
        }
        logging.info(f"Inserting feedback: {feedback_data}")

        # Insert Feedback
        result = await feedback_collection.insert_one(feedback_data)
        if not result.inserted_id:
            logging.error(f"Failed to insert feedback for poll {poll_id}")
            raise HTTPException(status_code=500, detail="Failed to add feedback")

        # Send notification
        background_tasks.add_task(
            send_feedback_notification,
            commenter, poll["activity_title"], poll_id
        )
        logging.info(f"Feedback added for poll {poll_id} by {commenter}")

        return RedirectResponse(url=f"/polls/dashboard/{poll_id}", status_code=303)
    except ValidationError as ve:
        logging.error(f"Validation error: {ve}")
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        logging.error(f"Unexpected error while adding feedback: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while adding feedback")

def is_valid_objectid(id_str):
    try:
        ObjectId(id_str)
        return True
    except:
        return False

# List Feedback
@router.get("/list")
async def list_feedback(poll_id: str, request: Request):
    try:
        logging.info(f"Fetching feedback for poll {poll_id}")

        if not is_valid_objectid(poll_id):
            logging.error(f"Invalid poll_id format: {poll_id}")
            raise HTTPException(status_code=400, detail="Invalid poll ID format")

        # Retrieve the poll
        poll = await polls_collection.find_one({"_id": ObjectId(poll_id)})
        if not poll:
            logging.error(f"Poll {poll_id} not found.")
            raise HTTPException(status_code=404, detail="Poll not found")

        # Authorization Check
        guest_email = request.query_params.get("email")
        is_authorized = (
            poll.get("is_public", True) or
            (guest_email and guest_email in poll.get("participants", []))
        )

        if not is_authorized:
            logging.warning(f"Unauthorized access to feedback for poll {poll_id}")
            raise HTTPException(status_code=403, detail="Not authorized to view feedback")

        # Fetch feedback
        feedback_cursor = feedback_collection.find({"poll_id": str(poll_id)})
        feedback_list = await feedback_cursor.to_list(length=100)

        # Serialize feedback data
        serialized_feedback = [serialize_document(feedback) for feedback in feedback_list]
        logging.debug(f"Feedback retrieved: {serialized_feedback}")

        return serialized_feedback
    except Exception as e:
        logging.error(f"Error fetching feedback for poll ID {poll_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch feedback")

# Retrieve Comments for a Poll
@router.get("/poll/{poll_id}/comments")
async def get_poll_feedback(poll_id: str, current_user: dict = Depends(get_current_user)):
    logging.info(f"Retrieving comments for poll {poll_id}")

    # Validate Poll
    poll = await polls_collection.find_one({"_id": ObjectId(poll_id)})
    if not poll:
        logging.error(f"Poll {poll_id} not found.")
        raise HTTPException(status_code=404, detail="Poll not found")

    # Authorization
    user_email = current_user.get("email") if current_user else None
    user_username = current_user.get("username") if current_user else None
    is_creator = current_user and current_user.get("username") == poll["creator"]
    is_participant = user_email and user_email in poll.get("participants", [])

    if not (is_creator or is_participant):
        logging.warning(
            f"Unauthorized attempt to view comments for poll {poll_id} by "
            f"{user_email or user_username or 'unknown user'}."
        )
        raise HTTPException(status_code=403, detail="User not authorized to view comments for this poll")

    # Fetch Comments
    try:
        feedback_cursor = feedback_collection.find({"poll_id": poll_id})
        feedback_list = await feedback_cursor.to_list(length=100)
        logging.info(f"Comments retrieved for poll {poll_id}. Count: {len(feedback_list)}")
        return feedback_list
    except Exception as e:
        logging.error(f"Error retrieving comments for poll {poll_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch comments")
