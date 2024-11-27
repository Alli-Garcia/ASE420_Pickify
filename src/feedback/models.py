# src/feedback/models.py

from pydantic import BaseModel

class Feedback(BaseModel):
    poll_title: str
    commenter: str
    comment: str
