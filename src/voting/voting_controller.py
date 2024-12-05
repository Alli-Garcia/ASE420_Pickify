from fastapi import APIRouter, HTTPException, Form, Request
from fastapi.responses import RedirectResponse
from starlette.status import HTTP_404_NOT_FOUND, HTTP_400_BAD_REQUEST
from src.database import database
from bson import ObjectId
from jose import jwt, JWTError
from src.config import SECRET_KEY, ALGORITHM
from src.authentication.auth_controller import get_current_user
import logging

router = APIRouter()

polls_collection = database.get_collection("polls")

@router.post("/vote")
async def vote(
    request: Request,
    poll_id: str = Form(...),
    option: str = Form(...),
    guest_email: str = Form(None),
):
    try:
        logging.info(f"Processing vote for poll ID: {poll_id}")

        # Validate and retrieve the poll
        if not ObjectId.is_valid(poll_id):
            logging.error(f"Invalid poll ID format: {poll_id}")
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Invalid poll ID format")
        
        poll = await polls_collection.find_one({"_id": ObjectId(poll_id)})
        if not poll:
            logging.error(f"Poll not found: {poll_id}")
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Poll not found")

        # Retrieve the current user (authenticated or guest)
        current_user = await get_current_user(request)
        # Determine voter ID
        voter_id = current_user["username"] if current_user else guest_email or "Anonymous"

        # Validate the selected option
        if option not in poll.get("options", []):
            logging.error(f"Invalid option selected: {option}")
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Invalid option selected")

        # Check if the voter has already voted
        if voter_id in poll.get("voters", []):
            logging.warning(f"Voter {voter_id} has already voted for poll ID: {poll_id}")
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="You have already voted")

        # Update the vote count and register the voter
        update_result = await polls_collection.update_one(
            {"_id": ObjectId(poll_id)},
            {
                "$inc": {f"votes.{option}": 1},  # Increment the vote count
                "$addToSet": {"voters": voter_id},  # Add voter to the list
            }
        )

        # Check if the update was successful
        if update_result.modified_count != 1:
            logging.error(f"Failed to update poll with vote for poll ID: {poll_id}")
            raise HTTPException(status_code=500, detail="Failed to record vote")

        logging.info(f"Vote recorded successfully for poll ID: {poll_id} by voter: {voter_id}")

        # Redirect to the analytics dashboard
        dashboard_url = f"/analytics/dashboard/{poll_id}"
        return RedirectResponse(url=dashboard_url, status_code=303)

    except HTTPException as http_exc:
        logging.error(f"HTTPException during voting: {http_exc.detail}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error during voting: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal server error occurred")
