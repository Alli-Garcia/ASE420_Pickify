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
from src.shared import templates
import logging

router = APIRouter()

# Polls collection from MongoDB
polls_collection = database.get_collection("polls")
feedback_collection = database.get_collection("feedback")

logging.basicConfig(level=logging.DEBUG)

@router.get("/", response_class=HTMLResponse)
async def list_polls(request: Request, current_user: dict = Depends(get_current_user)):
    try:
        logging.debug("Fetching list of polls...")
        polls_cursor = polls_collection.find({})
        polls = await polls_cursor.to_list(length=100)
        logging.info(f"Polls retrieved: {len(polls)}")
    except Exception as e:
        logging.error(f"Error fetching polls: {e}")
        raise HTTPException(status_code=500, detail="Unable to fetch polls at this time")

    return templates.TemplateResponse("polls.html", {"request": request, "polls": polls, "current_user": current_user})

@router.post("/create/type")
async def choose_poll_type(poll_type: str = Form(...)):
    """Handle poll type selection and redirect to the create poll page."""
    logging.info(f"Poll type selected: {poll_type}")
    if poll_type not in ["multiple_choice", "q_and_a", "wordcloud"]:
        logging.error(f"Invalid poll type: {poll_type}")
        raise HTTPException(status_code=400, detail="Invalid poll type")
    return RedirectResponse(url=f"/polls/create?poll_type={poll_type}", status_code=303)


@router.get("/create", response_class=HTMLResponse)
async def create_poll_form(request: Request, poll_type: str, current_user: dict = Depends(get_current_user)):
    """Render the create poll form."""
    if poll_type not in ["multiple_choice", "q_and_a", "wordcloud"]:
        raise HTTPException(status_code=400, detail="Invalid poll type")

    return templates.TemplateResponse(
        "create_poll.html",
        {"request": request, "poll_type": poll_type, "current_user": current_user},
    )

@router.post("/create")
async def create_poll(
    activity_title: str = Form(...),
    add_people: str = Form(...),
    set_timer: int = Form(...),
    poll_question: str = Form(...),
    num_options: int = Form(None),
    options: List[str] = Form(None),
    poll_type: str = Form(...),
    current_user: dict = Depends(get_current_user),
):
    """Create a new poll."""
    try:
        if poll_type == "multiple_choice" and (not options or len(options) < 2):
            raise HTTPException(status_code=400, detail="Multiple-choice polls require at least 2 options.")

        participants = [email.strip() for email in add_people.split(",") if email.strip()]
        poll = {
            "activity_title": activity_title,
            "participants": participants,
            "timer_minutes": set_timer,
            "creator": current_user["username"],
            "created_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=set_timer),
            "status": "active",
            "poll_question": poll_question,
            "options": options or [],
            "type": poll_type,
            "votes": {option: 0 for option in options or []},
            "voters": []
        }

        result = await polls_collection.insert_one(poll)
        if not result.inserted_id:
            raise HTTPException(status_code=500, detail="Failed to create poll.")

        poll_id = str(result.inserted_id)
        return RedirectResponse(url=f"/polls/dashboard/{poll_id}", status_code=303)
    except Exception as e:
        logging.error(f"Error during poll creation: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred while creating the poll")


@router.get("/{poll_id}", response_class=HTMLResponse)
async def view_poll(poll_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    """View a specific poll."""
    poll = await polls_collection.find_one({"_id": ObjectId(poll_id)})
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    return templates.TemplateResponse("poll.html", {"request": request, "poll": poll, "current_user": current_user})


@router.get("/dashboard/{poll_id}", response_class=HTMLResponse)
async def view_dashboard(poll_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    try:
        logging.debug(f"Accessing dashboard for poll ID: {poll_id}")
        poll = await polls_collection.find_one({"_id": ObjectId(poll_id)})
        if not poll:
            logging.error(f"Poll not found: {poll_id}")
            raise HTTPException(status_code=404, detail="Poll not found")

        # Check permissions
        is_creator = current_user and current_user["username"] == poll["creator"]
        is_participant = current_user["username"] in poll.get("participants", [])
        if not (is_creator or is_participant):
            logging.warning(f"Unauthorized access attempt to poll {poll_id}")
            raise HTTPException(status_code=403, detail="Not authorized to view this poll")

        # Fetch analytics
        total_votes = sum(poll["votes"].values())
        participation_rate = len(poll["participants"])
        logging.debug(f"Dashboard data prepared for poll ID: {poll_id}")

        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "poll_id": poll_id,
                "poll_title": poll["activity_title"],
                "poll_question": poll["poll_question"],
                "total_votes": total_votes,
                "participation_rate": participation_rate,
                "option_votes": poll["votes"],
            },
        )
    except Exception as e:
        logging.error(f"Error accessing dashboard for poll ID {poll_id}: {e}")
        raise HTTPException(status_code=500, detail="Unable to load poll dashboard")

@router.get("/analytics/{poll_id}")
async def poll_analytics(poll_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    try:
        logging.debug(f"Fetching analytics for poll ID: {poll_id}")

        # Ensure the poll exists
        poll = await polls_collection.find_one({"_id": ObjectId(poll_id)})
        if not poll:
            logging.error(f"Poll not found for analytics: {poll_id}")
            raise HTTPException(status_code=404, detail="Poll not found")

        # Ensure the current user is either the creator or a participant
        guest_email = request.query_params.get("email")
        is_authorized = (
            (current_user and current_user["username"] == poll["creator"]) or
            (current_user and current_user["username"] in poll.get("participants", [])) or
            (guest_email and guest_email in poll.get("participants", []))
        )

        if not is_authorized:
            logging.warning(f"Unauthorized access attempt to poll analytics: {poll_id}")
            raise HTTPException(status_code=403, detail="User not authorized to view analytics")

        # Prepare analytics data
        total_votes = sum(poll["votes"].values())
        option_votes = poll["votes"]
        participation_rate = len(poll["participants"])

        analytics_data = {
            "total_votes": total_votes,
            "option_votes": option_votes,
            "participation_rate": participation_rate
        }
        logging.debug(f"Analytics data prepared for poll ID: {poll_id}")

        return analytics_data
    except Exception as e:
        logging.error(f"Error fetching analytics for poll ID {poll_id}: {e}")
        raise HTTPException(status_code=500, detail="Unable to fetch poll analytics")
