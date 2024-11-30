from fastapi import APIRouter, HTTPException, Depends, Form, Request
from fastapi.responses import HTMLResponse
from src.authentication.utils import verify_token, get_current_user
from src.notifications.fcm_manager import send_notification
from src.websockets.connection_manager import manager
from datetime import datetime, timedelta, timezone
from src.database import database
from bson import ObjectId
from typing import List
from firebase_admin import messaging
from src.shared import templates

router = APIRouter()

# Polls collection from MongoDB
polls_collection = database.get_collection("polls")

# Function to get current user based on token
def get_current_user(token: str = Depends(verify_token)):
    username = verify_token(token)
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return username

@router.post("/create")
async def create_poll(
    activity_title: str = Form(...),
    add_people: str = Form(...),
    set_timer: int = Form(...),
    poll_question: str = Form(...),
    num_options: int = Form(...),
    options: List[str] = Form(...),
    current_user: str = Depends(get_current_user)
):
    # Ensure only authenticated users can create polls
    if not current_user:
        raise HTTPException(status_code=401, detail="User not authenticated")

    # Split the participants (comma-separated emails)
    participants = [email.strip() for email in add_people.split(",") if email.strip()]

    # Define the poll dictionary to be stored
    poll = {
        "activity_title": activity_title,
        "participants": participants,
        "timer_minutes": set_timer,
        "creator": current_user,
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=set_timer),
        "status": "active",
        "poll_question": poll_question,
        "options": options,
        "votes": {option: 0 for option in options},
    }

    # Insert the poll into MongoDB
    result = await polls_collection.insert_one(poll)

    # Confirm the poll was inserted
    if result.inserted_id:
        notification_title = f"New Poll: {activity_title}"
        notification_body = f"A new poll has been created: '{poll_question}'. You have been added as a participant."

        for participant in participants:
            await send_notification(participant, notification_title, notification_body)

        return {
            "message": "Poll created successfully",
            "poll_id": str(result.inserted_id),
            "poll": poll,
            "share_link": f"/polls/{result.inserted_id}"
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to create poll")

@router.get("/{poll_id}", response_class=HTMLResponse)
async def view_poll(poll_id: str, request: Request, current_user: str = Depends(get_current_user)):
    poll = await polls_collection.find_one({"_id": ObjectId(poll_id)})
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")

    return templates.TemplateResponse("poll.html", {"request": Request, "poll": poll, "current_user": current_user})

@router.get("/list")
async def list_polls(current_user: str = Depends(get_current_user)):
    # Fetch all polls created by the current user
    polls_cursor = polls_collection.find({"creator": current_user})
    polls = await polls_cursor.to_list(length=100)
    return polls

@router.put("/edit/{poll_id}")
async def edit_poll(
    poll_id: str,
    activity_title: str = Form(...),
    set_timer: int = Form(...),
    add_people: str = Form(...),
    current_user: str = Depends(get_current_user)
):
    # Find and update the poll if the current user is the creator
    poll = await polls_collection.find_one({"_id": ObjectId(poll_id), "creator": current_user})
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found or user not authorized to edit")

    participants = [email.strip() for email in add_people.split(",") if email.strip()]
    updated_data = {
        "activity_title": activity_title,
        "timer_minutes": set_timer,
        "participants": participants,
        "updated_at": datetime.now(timezone.utc)
    }

    result = await polls_collection.update_one({"_id": ObjectId(poll_id)}, {"$set": updated_data})

    if result.modified_count == 1:
        return {"message": "Poll updated successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to update poll")

@router.delete("/delete/{poll_id}")
async def delete_poll(poll_id: str, current_user: str = Depends(get_current_user)):
    # Find and delete the poll if the current user is the creator
    result = await polls_collection.delete_one({"_id": ObjectId(poll_id), "creator": current_user})
    if result.deleted_count == 1:
        return {"message": "Poll deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="Poll not found or user not authorized to delete")

@router.post("/{poll_id}/vote")
async def vote_on_poll(poll_id: str, option: str = Form(None), answer: str = Form(None), word: str = Form(None), current_user: str = Depends(get_current_user)):
    # Fetch the poll
    poll = await polls_collection.find_one({"_id": ObjectId(poll_id)})
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    
    if current_user not in poll["participants"]:
        raise HTTPException(status_code=403, detail="User not authorized to vote on this poll")

    # Ensure the selected option or answer is valid
    if poll["type"] == "multiple_choice":
        if option not in poll["options"]:
            raise HTTPException(status_code=400, detail="Invalid poll option")
        # Update the vote count
        poll["votes"][option] = poll["votes"].get(option, 0) + 1
    elif poll["type"] == "q_and_a":
        if not answer:
            raise HTTPException(status_code=400, detail="Answer cannot be empty")
        # Store the answer (this logic might need to be extended to save it properly)
        if "answers" not in poll:
            poll["answers"] = []
        poll["answers"].append({"user": current_user, "answer": answer})
    elif poll["type"] == "wordcloud":
        if not word:
            raise HTTPException(status_code=400, detail="Word cannot be empty")
        # Store the word (this logic might need to be extended to save it properly)
        if "words" not in poll:
            poll["words"] = {}
        poll["words"][word] = poll["words"].get(word, 0) + 1

    # Update the poll in the database
    result = await polls_collection.update_one(
        {"_id": ObjectId(poll_id)},
        {"$set": {"votes": poll.get("votes", {}), "answers": poll.get("answers", []), "words": poll.get("words", {})}}
    )

    if result.modified_count == 1:
        await manager.broadcast(f"Poll '{poll['poll_question']}' updated.")
        return {"message": "Vote recorded successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to record vote")

@router.get("/my_polls")
async def my_polls(current_user: str = Depends(get_current_user)):
    # Find polls where the current user is a participant
    user_polls_cursor = polls_collection.find({"participants": current_user})
    user_polls = await user_polls_cursor.to_list(length=100)
    return user_polls

@router.get("/analytics/{poll_id}")
async def poll_analytics(poll_id: str, current_user: str = Depends(get_current_user)):
    # Ensure the poll exists
    poll = await polls_collection.find_one({"_id": ObjectId(poll_id)})
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")

    # Ensure the current user is either the creator or a participant
    if current_user != poll["creator"] and current_user not in poll["participants"]:
        raise HTTPException(status_code=403, detail="User not authorized to view analytics")

    # Prepare analytics data
    total_votes = sum(poll["votes"].values())
    option_votes = poll["votes"]
    participation_rate = len(poll["participants"])  # Example, or use more detailed participation metrics

    analytics_data = {
        "total_votes": total_votes,
        "option_votes": option_votes,
        "participation_rate": participation_rate
    }

    return analytics_data
