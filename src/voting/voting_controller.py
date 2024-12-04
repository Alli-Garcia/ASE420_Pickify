# src/voting/voting_controller.py

from fastapi import APIRouter, HTTPException, Form, Request
from fastapi.responses import RedirectResponse
from starlette.status import HTTP_404_NOT_FOUND, HTTP_400_BAD_REQUEST
from src.database import database
from bson import ObjectId
from jose import jwt, JWTError
from src.config import SECRET_KEY, ALGORITHM
import logging

router = APIRouter()

polls_collection = database.get_collection("polls")

@router.post("/vote")
async def vote(
    poll_id: str = Form(...),
    option: str = Form(...),
    guest_email: str = Form(None),
    request: Request = None
):
    try:
        # Attempt to retrieve authenticated user from the token in cookies
        poll = await polls_collection.find_one({"_id": ObjectId(poll_id)})
        if not poll:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Poll not found")

        current_user = None
        token = request.cookies.get("Authorization")
        if token:
            try:
                scheme, token_value = token.split(" ", 1)
                if scheme.lower() == "bearer":
                    payload = jwt.decode(token_value, SECRET_KEY, algorithms=[ALGORITHM])
                    current_user = payload.get("sub")
            except (JWTError, ValueError):
                logging.warning("Failed to decode token for authentication. Treating as guest.")

        # Check if the selected option is valid
        if option not in poll["options"]:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Invalid option")

        # Determine voter ID (authenticated user, guest email, or "Anonymous")
        voter_id = current_user or guest_email or "Anonymous"

        # Check if the user has already voted
        if voter_id in poll.get("voters", []):
            raise HTTPException(status_code=400, detail="You have already voted")

        # Update the vote count for the selected option in the poll
        result = await polls_collection.update_one(
            {"_id": ObjectId(poll_id)},
            {
                "$inc": {f"votes.{option}": 1},
                "$addToSet": {"voters": voter_id},
            },
        )

        # Confirm the vote has been successfully updated
        if result.modified_count == 1:
            dashboard_url = f"/polls/dashboard/{poll_id}"
            return RedirectResponse(url=dashboard_url, status_code=303)
        else:
            raise HTTPException(status_code=500, detail="Failed to record vote")
    except Exception as e:
        logging.error(f"Error during voting: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")
