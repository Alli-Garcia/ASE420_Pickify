# src/polls/poll_controller.py

from fastapi import APIRouter, HTTPException, Depends
from src.authentication.utils import verify_token
from .models import Poll
from typing import List

router = APIRouter()

# Temporary in-memory poll store
poll_db = []

def get_current_user(token: str = Depends(verify_token)):
    username = verify_token(token)
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return username

@router.post("/create")
async def create_poll(poll: Poll, current_user: str = Depends(get_current_user)):
    # Ensure only authenticated users can create polls
    poll.creator = current_user
    poll_db.append(poll)
    return {"message": "Poll created successfully", "poll": poll}
    poll_db.append(poll)
    return {"message": "Poll created successfully", "poll": poll}

@router.get("/list", response_model=List[Poll])
async def list_polls():
    return poll_db

@router.put("/edit/{poll_title}")
async def edit_poll(poll_title: str, updated_poll: Poll, current_user: str = Depends(get_current_user)):
    for poll in poll_db:
        if poll.title == poll_title and poll.creator == current_user:
            poll.title = updated_poll.title
            poll.options = updated_poll.options
            return {"message": "Poll updated successfully"}
    raise HTTPException(status_code=404, detail="Poll not found or user not authorized to edit")

@router.delete("/delete/{poll_title}")
async def delete_poll(poll_title: str, current_user: str = Depends(get_current_user)):
    for poll in poll_db:
        if poll.title == poll_title and poll.creator == current_user:
            poll_db.remove(poll)
            return {"message": "Poll deleted successfully"}
    raise HTTPException(status_code=404, detail="Poll not found or user not authorized to delete")

@router.post("/vote")
async def vote(poll_title: str, option: str, current_user: str = Depends(get_current_user)):
    for poll in poll_db:
        if poll.title == poll_title:
            if option not in poll.options:
                raise HTTPException(status_code=400, detail="Invalid poll option")
            if 'votes' not in poll:
                poll.votes = {}
            poll.votes[option] = poll.votes.get(option, 0) + 1
            return {"message": f"Vote recorded for {option}"}
    raise HTTPException(status_code=404, detail="Poll not found")
