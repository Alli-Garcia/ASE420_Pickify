#poll_controller.py
from fastapi import APIRouter, HTTPException, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from src.authentication.auth_controller import get_current_user
from src.notifications.fcm_manager import send_notification
from src.authentication.utils import send_email
from src.websockets.connection_manager import manager
from datetime import datetime, timedelta, timezone
from src.database import database, device_tokens_collection, users_collection
from bson import ObjectId
from typing import List
from src.shared import templates, polls_collection
import logging
router = APIRouter()

# Polls collection from MongoDB
polls_collection = database.get_collection("polls")

@router.get("/", response_class=HTMLResponse)
async def list_polls(request: Request, current_user: dict = Depends(get_current_user)):
    try:
        polls_cursor = polls_collection.find({})
        polls = await polls_cursor.to_list(length=100)
        print(polls)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Unable to fetch polls at this time")

    return templates.TemplateResponse("polls.html", {"request": request, "polls": polls, "current_user": current_user})

@router.post("/create")
async def create_poll(
    activity_title: str = Form(...),
    add_people: str = Form(...),
    set_timer: int = Form(...),
    poll_question: str = Form(...),
    num_options: int = Form(None),
    options: List[str] = Form(None),
    poll_type: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    # Split participants' emails
    participants = [email.strip() for email in add_people.split(",") if email.strip()]

    # Poll data to save
    poll = {
        "activity_title": activity_title,
        "participants": participants,
        "timer_minutes": set_timer,
        "creator": current_user["username"],  # Assumes current_user includes 'username'
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=set_timer),
        "status": "active",
        "poll_question": poll_question,
        "options": options or [],
        "type": poll_type,
        "votes": {option: 0 for option in options or []},
        "voters": []  # Tracks users who voted
    }

    # Insert the poll and retrieve its ID
    result = await polls_collection.insert_one(poll)
    if not result.inserted_id:
        raise HTTPException(status_code=500, detail="Failed to create poll")
    poll_id = str(result.inserted_id)  # Convert ObjectId to string

    # Initialize collections for tokens and guest links
    participant_tokens = []
    guest_links = []

    for email in participants:
        user = await users_collection.find_one({"email": email})
        if user:
            # Fetch device tokens for registered users
            tokens_cursor = device_tokens_collection.find({"user_id": user["_id"]})
            tokens = await tokens_cursor.to_list(length=100)
            if tokens:
                participant_tokens.extend([token["device_token"] for token in tokens])
        else:
            # Generate guest links for unregistered users
            poll_link = f"https://pickify.onrender.com/polls/guest/{email}?poll_id={poll_id}"
            guest_links.append({"email": email, "link": poll_link})

    # Send FCM notifications to registered users
    for token in participant_tokens:
        await send_notification(
            device_token=token,
            title=f"New Poll: {activity_title}",
            body=f"{poll_question}\nParticipate: https://pickify.onrender.com/polls/{poll_id}"
        )

    # Send emails to unregistered users with guest links
    for guest in guest_links:
        send_email(
            to=guest["email"],
            subject=f"You're invited to a poll: {activity_title}",
            body=f"Click the link to participate: {guest['link']}"
        )

    return {"message": "Poll created successfully"}


@router.get("/guest/{email}", response_class=HTMLResponse)
async def guest_access_poll(email: str, poll_id: str, request: Request):
    # Find the poll
    poll = await polls_collection.find_one({"_id": ObjectId(poll_id)})
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")

    # Allow guest access
    return templates.TemplateResponse(
        "poll_guest.html",
        {
            "request": request,
            "poll": poll,
            "email": email
        }
    )

@router.get("/create", response_class=HTMLResponse)
async def create_poll_form(request: Request, poll_type: str, current_user: dict = Depends(get_current_user)):
    if poll_type not in ["multiple_choice", "q_and_a", "wordcloud"]:
        raise HTTPException(status_code=400, detail="Invalid poll type")

    return templates.TemplateResponse(
        "create_poll.html",
        {"request": request, "poll_type": poll_type, "current_user": current_user},
    )

@router.post("/create/type")
async def choose_poll_type(poll_type: str = Form(...)):
    if poll_type not in ["multiple_choice", "q_and_a", "wordcloud"]:
        raise HTTPException(status_code=400, detail="Invalid poll type")
    return RedirectResponse(url=f"/polls/create?poll_type={poll_type}", status_code=303)

@router.get("/{poll_id}", response_class=HTMLResponse)
async def view_poll(poll_id: str, request: Request, current_user: str = Depends(get_current_user)):
    poll = await polls_collection.find_one({"_id": ObjectId(poll_id)})
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    print(f"Poll retrieved: {poll}")
    return templates.TemplateResponse("poll.html", {"request": request, "poll": poll, "current_user": current_user})

@router.get("/created-by-me", response_class=HTMLResponse)
async def polls_created_by_me(request: Request, current_user: dict = Depends(get_current_user)):
    try:
        polls_cursor = polls_collection.find({"creator": current_user["username"]})
        polls = await polls_cursor.to_list(length=100)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching polls created by user: {e}")

    return templates.TemplateResponse("polls_created_by_me.html", {"request": request, "polls": polls, "current_user": current_user})

@router.get("/shared-with-me", response_class=HTMLResponse)
async def polls_shared_with_me(request: Request, current_user: dict = Depends(get_current_user)):
    try:
        polls_cursor = polls_collection.find({"participants": {"$in": [current_user["username"]]}})
        polls = await polls_cursor.to_list(length=100)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching polls shared with user: {e}")

    return templates.TemplateResponse("polls_shared_with_me.html", {"request": request, "polls": polls, "current_user": current_user})

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
async def vote_on_poll(
    poll_id: str,
    option: str = Form(None),
    answer: str = Form(None),
    word: str = Form(None),
    email: str = Form(None),  # Add email for guests
    current_user: str = Depends(get_current_user)
):
    poll = await polls_collection.find_one({"_id": ObjectId(poll_id)})
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")

    # Determine the voter
    voter = current_user if current_user else email

    # Check if the voter has already voted
    if voter in poll.get("voters", []):
        raise HTTPException(status_code=403, detail="User has already voted on this poll")

    # Record the vote
    if poll["type"] == "multiple_choice":
        if option not in poll["options"]:
            raise HTTPException(status_code=400, detail="Invalid poll option")
        await polls_collection.update_one(
            {"_id": ObjectId(poll_id)},
            {"$inc": {f"votes.{option}": 1}, "$push": {"voters": voter}}
        )
    elif poll["type"] == "q_and_a":
        if not answer:
            raise HTTPException(status_code=400, detail="Answer cannot be empty")
        await polls_collection.update_one(
            {"_id": ObjectId(poll_id)},
            {"$push": {"answers": {"user": voter, "answer": answer}}, "$push": {"voters": voter}}
        )
    elif poll["type"] == "wordcloud":
        if not word:
            raise HTTPException(status_code=400, detail="Word cannot be empty")
        await polls_collection.update_one(
            {"_id": ObjectId(poll_id)},
            {"$push": {"words": {"word": word, "count": 1}}, "$push": {"voters": voter}}
        )

    return RedirectResponse(url=f"/polls/dashboard/{poll_id}", status_code=303)

@router.get("/my_polls")
async def my_polls(current_user: str = Depends(get_current_user)):
    # Find polls where the current user is a participant
    user_polls_cursor = polls_collection.find({"participants": current_user})
    user_polls = await user_polls_cursor.to_list(length=100)
    return user_polls


@router.get("/dashboard/{poll_id}", response_class=HTMLResponse)
async def view_dashboard(poll_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    # Retrieve the poll
    poll = await polls_collection.find_one({"_id": ObjectId(poll_id)})

    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    if current_user and (current_user["username"] == poll["creator"] or current_user["username"] in poll["participants"]):
        authorized_user = current_user["username"]
    elif not current_user:
        authorized_user = request.query_params.get("email")
        if authorized_user not in poll["participants"]:
            raise HTTPException(status_code=403, detail="User not authorized to view this poll")
    else:
        raise HTTPException(status_code=403, detail="User not authorized to view this poll")

    # Calculate analytics
    total_votes = sum(poll["votes"].values())
    participation_rate = len(poll["participants"])
    option_votes = poll["votes"]

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "poll_id": poll_id,
            "poll_title": poll.get("activity_title"),
            "poll_question": poll.get("poll_question", ""),
            "total_votes" : sum(poll["votes"].values()),
            "participation_rate": len(poll["participants"]),
            "option_votes": poll["votes"],
            "voters": poll.get("voters", [])
        },
    )


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
