# src/polls/poll_controller.py

from fastapi import APIRouter, HTTPException
from .models import Poll
from typing import List

router = APIRouter()

# Temporary in-memory poll store
poll_db = []

@router.post("/create")
async def create_poll(poll: Poll):
    poll_db.append(poll)
    return {"message": "Poll created successfully", "poll": poll}

@router.get("/list", response_model=List[Poll])
async def list_polls():
    return poll_db
