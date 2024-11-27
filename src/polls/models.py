# src/polls/models.py

from pydantic import BaseModel
from typing import List
from typing import Dict

class Poll(BaseModel):
    title: str
    options: List[str]
    votes: Dict[str, int] = {}
    creator: str  # This will reference the username of the creator for now
    is_active: bool = True
