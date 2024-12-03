# src/feedback/models.py

from pydantic import BaseModel

class Feedback(BaseModel):
    poll_id: str  # Add this field to match the expected input
    comment: str
    commenter: str
