# src/feedback/feedback_controller.py

from fastapi import APIRouter
from .models import Feedback
from typing import List

router = APIRouter()

# Temporary in-memory feedback store
feedback_db = []

@router.post("/add")
async def add_feedback(feedback: Feedback):
    feedback_db.append(feedback)
    return {"message": "Feedback added successfully"}

@router.get("/list", response_model=List[Feedback])
async def list_feedback(poll_title: str):
    feedback_for_poll = [feedback for feedback in feedback_db if feedback.poll_title == poll_title]
    return feedback_for_poll
