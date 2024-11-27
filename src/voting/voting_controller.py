# src/voting/voting_controller.py

from fastapi import APIRouter, HTTPException
from src.polls.models import Poll
from src.polls.poll_controller import poll_db

router = APIRouter()

@router.post("/vote")
async def vote(poll_title: str, option: str):
    for poll in poll_db:
        if poll.title == poll_title:
            if option not in poll.options:
                raise HTTPException(status_code=400, detail="Invalid option")
            if option not in poll.votes:
                poll.votes[option] = 1
            else:
                poll.votes[option] += 1
            return {"message": f"Vote recorded for {option}"}
    raise HTTPException(status_code=404, detail="Poll not found")
