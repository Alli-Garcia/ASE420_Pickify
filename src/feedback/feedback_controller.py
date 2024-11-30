# src/feedback/feedback_controller.py

from fastapi import APIRouter, Depends, HTTPException, Form, BackgroundTasks
from src.authentication.auth_controller import get_current_user
from src.notifications.fcm_manager import send_feedback_notification
from src.database import database
from bson import ObjectId
from pydantic import BaseModel
from .models import Feedback
from typing import List
from datetime import datetime

router = APIRouter()

feedback_collection = database.get_collection("feedback")
polls_collection = database.get_collection("polls")
class Feedback(BaseModel):
    poll_title: str
    commenter: str
    comment: str

@router.post("/add")
async def add_feedback(
    background_tasks: BackgroundTasks,  # Removed `Depends()` and used directly
    poll_id: str = Form(...),
    comment: str = Form(...),
    current_user: str = Depends(get_current_user)
):
    poll = await polls_collection.find_one({"_id": ObjectId(poll_id)})
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")

    # Prepare feedback data
    feedback_data = {
        "poll_id": poll_id,
        "comment": comment,
        "commenter": current_user,
        "created_at": datetime.now()
    }

    # Insert feedback into MongoDB
    result = await feedback_collection.insert_one(feedback_data)

    # Confirm feedback was saved
    if result.inserted_id:
        # Send FCM notification about the new feedback
        background_tasks.add_task(send_feedback_notification, current_user, poll["activity_title"], poll_id)

        return {"message": "Feedback added successfully", "feedback_id": str(result.inserted_id)}
    else:
        raise HTTPException(status_code=500, detail="Failed to add feedback")

@router.get("/list")
async def list_feedback(poll_id: str):
    poll = await polls_collection.find_one({"_id": ObjectId(poll_id)})
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")

    # Fetch feedback for the specified poll from MongoDB
    feedback_cursor = feedback_collection.find({"poll_id": poll_id})
    feedback_for_poll = await feedback_cursor.to_list(length=100)

    return feedback_for_poll

@router.get("/poll/{poll_id}/comments")
async def get_poll_feedback(poll_id: str, current_user: str = Depends(get_current_user)):
    # Ensure the poll exists
    poll = await polls_collection.find_one({"_id": ObjectId(poll_id)})
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")

    # Ensure the current user is a participant
    if current_user not in poll["participants"]:
        raise HTTPException(status_code=403, detail="User not authorized to view feedback")

    # Fetch feedback for the poll
    feedback_cursor = feedback_collection.find({"poll_id": poll_id})
    feedback_list = await feedback_cursor.to_list(length=100)

    return feedback_list
