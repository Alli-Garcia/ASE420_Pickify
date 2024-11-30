# src/voting/voting_controller.py

from fastapi import APIRouter, HTTPException, Depends, Form
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from starlette.status import HTTP_404_NOT_FOUND, HTTP_400_BAD_REQUEST
from src.authentication.auth_controller import get_current_user
from src.database import database

router = APIRouter()

polls_collection = database.get_collection("polls")

@router.post("/vote")
async def vote(
    poll_id: str = Form(...), 
    option: str = Form(...), 
    current_user: str = Depends(get_current_user)):
    poll = await polls_collection.find_one({"_id": ObjectId(poll_id)})
    if not poll:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Poll not found")

    # Check if the selected option is valid
    if option not in poll["options"]:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Invalid option")

    # Update the vote count for the selected option in the poll
    result = await polls_collection.update_one(
        {"_id": ObjectId(poll_id)},
        {"$inc": {f"votes.{option}": 1}}
    )

    # Confirm the vote has been successfully updated
    if result.modified_count == 1:
        return {"message": f"Vote recorded for option '{option}'"}
    else:
        raise HTTPException(status_code=500, detail="Failed to record vote")
