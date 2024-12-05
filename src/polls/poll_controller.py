from fastapi import APIRouter, HTTPException, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security.utils import get_authorization_scheme_param
from jose import JWTError, jwt
from src.config import SECRET_KEY, ALGORITHM
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

    if not current_user:  # Check if the user is authenticated
        # Redirect to login page if not authenticated
        return RedirectResponse(url="/auth/login", status_code=303)

    """Render the create poll form."""
    if poll_type not in ["multiple_choice", "q_and_a", "wordcloud"]:
        raise HTTPException(status_code=400, detail="Invalid poll type")

    return templates.TemplateResponse(
        "create_poll.html",
        {"request": request, "poll_type": poll_type, "current_user": current_user},
    )

@router.post("/create")
async def create_poll(
    request: Request,
    activity_title: str = Form(...),
    add_people: str = Form(...),
    set_timer: int = Form(...),
    poll_question: str = Form(...),
    num_options: int = Form(None),
    options: List[str] = Form(None),
    poll_type: str = Form(...),
    current_user: dict = Depends(get_current_user),
):
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
            "voters": [],
            "is_public" : True,
            "questions" : [] if poll_type == "q_and_a" else None
        }

        result = await polls_collection.insert_one(poll)
        if not result.inserted_id:
            raise HTTPException(status_code=500, detail="Failed to create poll.")

        poll_id = str(result.inserted_id)
        poll_url = f"{request.base_url}polls/{poll_id}"  # Construct poll URL


        # Email notification
        subject = f"You're invited to participate in a poll: {activity_title}"
        body = (f"{current_user['username']} has invited you to participate in a poll: {poll_question}"
        f"Click the link below to participate:\n{poll_url}\n\n")
        send_email(participants, subject, body)

        return RedirectResponse(url=f"/analytics/{result.inserted_id}", status_code=303)
    except Exception as e:
        logging.error(f"Error creating poll: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while creating the poll")

@router.get("/{poll_id}", response_class=HTMLResponse)
async def view_poll(poll_id: str, request: Request):
    """View a specific poll."""
    try:
        # Fetch the poll from the database
        poll = await polls_collection.find_one({"_id": ObjectId(poll_id)})
        if not poll:
            raise HTTPException(status_code=404, detail="Poll not found")

        # Always allow access for public polls
        if not poll.get("is_public", False):
            logging.warning(f"Attempt to access private poll {poll_id}")
            raise HTTPException(status_code=403, detail="This poll is private")

        # Get guest email from query params
        guest_email = request.query_params.get("email")
        user_display = guest_email or "Guest"

        logging.info(f"Rendering poll {poll_id} for user: {user_display}")
        return templates.TemplateResponse(
            "poll.html",
            {"request": request, "poll": poll, "current_user": {"username": user_display}},
        )
    except Exception as e:
        logging.error(f"Error accessing poll {poll_id}: {e}")
        raise HTTPException(status_code=500, detail="Unable to load poll")

@router.get("/analytics/{poll_id}")
async def poll_analytics(poll_id: str, request: Request):
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
            poll.get("is_public", True) or  # Allow access if the poll is public
            (guest_email and guest_email in poll.get("participants", []))
        )

        if not is_authorized:
            logging.warning(f"Unauthorized access attempt to poll analytics: {poll_id}")
            raise HTTPException(status_code=403, detail="User not authorized to view analytics")

        if poll["type"] == "q_and_a":
            questions = poll.get("questions", [])
            analytics_data = {
                "questions": questions,
                "total_participants": len(poll.get("participants", [])),
            }
        else:
            total_votes = sum(poll["votes"].values())
            option_votes = poll["votes"]
            analytics_data = {
                "total_votes": total_votes,
                "option_votes": option_votes,
                "participation_rate": len(poll["participants"]),
            }

        logging.debug(f"Analytics data prepared for poll ID: {poll_id}")

        return analytics_data
    except Exception as e:
        logging.error(f"Error fetching analytics for poll ID {poll_id}: {e}")
        raise HTTPException(status_code=500, detail="Unable to fetch poll analytics")

@router.get("/edit/{poll_id}", response_class=HTMLResponse)
async def edit_poll_form(poll_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    """Render the edit poll form with existing poll data."""
    try:
        logging.info(f"Fetching poll {poll_id} for editing")

        # Fetch the poll from the database
        poll = await polls_collection.find_one({"_id": ObjectId(poll_id)})
        if not poll:
            logging.error(f"Poll {poll_id} not found")
            raise HTTPException(status_code=404, detail="Poll not found")

        # Check if the current user is the creator of the poll
        if poll["creator"] != current_user["username"]:
            logging.warning(f"Unauthorized attempt to edit poll {poll_id} by user {current_user['username']}")
            raise HTTPException(status_code=403, detail="Not authorized to edit this poll")

        # Render the form with existing poll data
        return templates.TemplateResponse(
            "create_poll.html",
            {
                "request": request,
                "poll_id": poll_id,
                "poll_type": poll["type"],
                "activity_title": poll["activity_title"],
                "poll_question": poll["poll_question"],
                "options": poll["options"],
                "timer_minutes": poll["timer_minutes"],
                "participants": ", ".join(poll["participants"]),
                "current_user": current_user,
                "poll_creator": poll.get("creator"),  # Add this line
                "current_user": current_user
            },
        )
    except Exception as e:
        logging.error(f"Error loading edit form for poll {poll_id}: {e}")
        raise HTTPException(status_code=500, detail="Unable to load edit form")

@router.post("/edit/{poll_id}")
async def edit_poll(
    poll_id: str,
    request: Request,
    activity_title: str = Form(...),
    add_people: str = Form(...),
    set_timer: int = Form(...),
    poll_question: str = Form(...),
    num_options: int = Form(None),
    options: List[str] = Form(None),
    poll_type: str = Form(...),
    current_user: dict = Depends(get_current_user),
):
    """Handle poll editing."""
    try:
        logging.info(f"Editing poll {poll_id}")

        # Fetch the poll to verify permissions
        poll = await polls_collection.find_one({"_id": ObjectId(poll_id)})
        if not poll:
            logging.error(f"Poll {poll_id} not found")
            raise HTTPException(status_code=404, detail="Poll not found")

        if poll["creator"] != current_user["username"]:
            logging.warning(f"Unauthorized attempt to edit poll {poll_id} by user {current_user['username']}")
            raise HTTPException(status_code=403, detail="Not authorized to edit this poll")

        # Update the poll data
        participants = [email.strip() for email in add_people.split(",") if email.strip()]
        updated_poll = {
            "activity_title": activity_title,
            "participants": participants,
            "timer_minutes": set_timer,
            "poll_question": poll_question,
            "options": options or [],
            "type": poll_type,
            "updated_at": datetime.now(timezone.utc),
        }

        result = await polls_collection.update_one(
            {"_id": ObjectId(poll_id)},
            {"$set": updated_poll},
        )

        if result.modified_count == 0:
            logging.error(f"Failed to update poll {poll_id}")
            raise HTTPException(status_code=500, detail="Failed to update poll")

        logging.info(f"Poll {poll_id} updated successfully")

        return RedirectResponse(url=f"/analytics/dashboard/{poll_id}", status_code=303)
    except Exception as e:
        logging.error(f"Error updating poll {poll_id}: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while updating the poll")

@router.get("/shared-with-me", response_class=HTMLResponse)
async def polls_shared_with_me(request: Request, current_user: dict = Depends(get_current_user)):
    """List polls shared with the current user."""
    try:
        logging.info(f"Fetching polls shared with user {current_user['username']}")

        polls_cursor = polls_collection.find({"participants": {"$in": [current_user["email"]]}})
        polls = await polls_cursor.to_list(length=100)
        logging.info(f"Polls shared with user retrieved: {len(polls)}")

        return templates.TemplateResponse("shared_with_me.html", {"request": request, "polls": polls})
    except Exception as e:
        logging.error(f"Error fetching polls shared with user: {e}")
        raise HTTPException(status_code=500, detail="Unable to fetch polls")

@router.get("/created-by-me", response_class=HTMLResponse)
async def polls_created_by_me(request: Request, current_user: dict = Depends(get_current_user)):
    """List polls created by the current user."""
    try:
        logging.info(f"Fetching polls created by user {current_user['username']}")

        polls_cursor = polls_collection.find({"creator": current_user["username"]})
        polls = await polls_cursor.to_list(length=100)
        logging.info(f"Polls created by user retrieved: {len(polls)}")

        return templates.TemplateResponse("created_by_me.html", {"request": request, "polls": polls})
    except Exception as e:
        logging.error(f"Error fetching polls created by user: {e}")
        raise HTTPException(status_code=500, detail="Unable to fetch polls")

@router.post("/polls/{poll_id}/questions")
async def submit_question(
    poll_id: str,
    question: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    try:
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required to submit questions")

        poll = await polls_collection.find_one({"_id": ObjectId(poll_id)})
        if not poll:
            raise HTTPException(status_code=404, detail="Poll not found")

        if poll["poll_type"] != "q_and_a":
            raise HTTPException(status_code=400, detail="This poll does not accept questions")

        new_question = {
            "question_id": ObjectId(),
            "question": question,
            "author": current_user["username"] if current_user else "Guest",
            "created_at": datetime.now(timezone.utc),
            "answers": []
        }

        result = await polls_collection.update_one(
            {"_id": ObjectId(poll_id)},
            {"$push": {"questions": new_question}}
        )

        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to add question")

        return RedirectResponse(url=f"/analytics/dashboard/{poll_id}", status_code=303)
    except Exception as e:
        logging.error(f"Error submitting question: {e}")
        raise HTTPException(status_code=500, detail="Unable to submit question")

@router.post("/polls/{poll_id}/questions/{question_id}/answers")
async def submit_answer(
    poll_id: str,
    question_id: str,
    answer: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    try:
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required to submit answers")

        poll = await polls_collection.find_one({"_id": ObjectId(poll_id)})
        if not poll:
            raise HTTPException(status_code=404, detail="Poll not found")

        if poll["poll_type"] != "q_and_a":
            raise HTTPException(status_code=400, detail="This poll does not accept answers")

        new_answer = {
            "answer_id": ObjectId(),
            "answer": answer,
            "author": current_user["username"],
            "created_at": datetime.now(timezone.utc)
        }

        result = await polls_collection.update_one(
            {
                "_id": ObjectId(poll_id),
                "questions.question_id": ObjectId(question_id)
            },
            {"$push": {"questions.$.answers": new_answer}}
        )

        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to add answer")

        return RedirectResponse(url=f"/analytics/dashboard/{poll_id}", status_code=303)
    except Exception as e:
        logging.error(f"Error submitting answer: {e}")
        raise HTTPException(status_code=500, detail="Unable to submit answer")
