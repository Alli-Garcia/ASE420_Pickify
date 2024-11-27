# src/feedback/feedback_controller.py

from fastapi import APIRouter, Depends, HTTPException
from src.authentication.auth_controller import get_current_user
from src.polls.poll_controller import poll_db
from pydantic import BaseModel
from .models import Feedback
from typing import List

router = APIRouter()

# Temporary in-memory feedback store
feedback_db = []
class Feedback(BaseModel):
    poll_title: str
    commenter: str
    comment: str

@router.post("/add")
async def add_feedback(feedback: Feedback, current_user: str = Depends(get_current_user)):
    if not any(poll.title == feedback.poll_title for poll in poll_db):
        raise HTTPException(status_code=404, detail="Poll not found")

    feedback.commenter = current_user  # Add authenticated username to feedback
    feedback_db.append(feedback)
    return {"message": "Feedback added successfully"}

@router.get("/list")
async def list_feedback(poll_title: str):
    if not any(poll.title == poll_title for poll in poll_db):
        raise HTTPException(status_code=404, detail="Poll not found")

    feedback_for_poll = [f for f in feedback_db if f.poll_title == poll_title]
    return feedback_for_poll
