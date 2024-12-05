import matplotlib.pyplot as plt
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import FileResponse, HTMLResponse
from bson import ObjectId
from src.database import database
from src.authentication.auth_controller import get_current_user
from src.shared import templates
import os
import logging
router = APIRouter()
logging.basicConfig(level=logging.DEBUG)
# MongoDB Collection
polls_collection = database.get_collection("polls")

feedback_collection = database.get_collection("feedback")

@router.get("/report/{poll_id}")
async def poll_report(poll_id: str):
    # Find the poll by its ID
    poll = await polls_collection.find_one({"_id": ObjectId(poll_id)})
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")

    # Extract options and votes from the poll
    options = list(poll["votes"].keys())
    votes = list(poll["votes"].values())

    # Generate the bar chart of poll results
    plt.figure(figsize=(10, 6))  # Set the figure size for the chart
    plt.bar(options, votes, color='blue', alpha=0.7)
    plt.xlabel('Options')
    plt.ylabel('Votes')
    plt.title(f"Results for Poll: {poll['activity_title']}")
    plt.xticks(rotation=45, ha="right")  # Rotate the x-axis labels if needed

    # Define the file path for saving the report
    report_filename = f"{poll_id}_report.png"
    plt.tight_layout()  # Adjust the layout for better spacing
    plt.savefig(report_filename)
    plt.close()  # Close the plot to release memory

    # Return the report as a downloadable file and clean up after sending
    try:
        return FileResponse(path=report_filename, media_type="image/png", filename=report_filename)
    finally:
        if os.path.exists(report_filename):
            os.remove(report_filename)


@router.get("/dashboard/{poll_id}", response_class=HTMLResponse)
async def view_dashboard(poll_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    try:
        logging.debug(f"Loading dashboard for poll ID: {poll_id}")

        if not ObjectId.is_valid(poll_id):
            logging.error(f"Invalid poll ID format: {poll_id}")
            raise HTTPException(status_code=400, detail="Invalid poll ID format")


        # Retrieve the poll
        poll = await polls_collection.find_one({"_id": ObjectId(poll_id)})
        if not poll:
            logging.error(f"Poll {poll_id} not found")
            raise HTTPException(status_code=404, detail="Poll not found")

        # Determine the user (authenticated or guest)
        guest_email = request.query_params.get("email")
        user_id = current_user.get("username") if current_user else guest_email or "Anonymous"

        # Authorization checks
        is_creator = current_user and current_user.get("username") == poll["creator"]
        is_voter = user_id in poll.get("voters", [])
        is_participant = user_id in poll.get("participants", [])
        is_public = poll.get("is_public", True)

        if not (is_creator or is_voter or is_participant or is_public):
            logging.warning(f"Unauthorized access to dashboard for poll ID: {poll_id}")
            raise HTTPException(status_code=403, detail="Not authorized to view this dashboard")
        if is_voter and user_id not in poll.get("voters", []):
            await polls_collection.update_one(
                {"_id": ObjectId(poll_id)},
                {"$addToSet": {"voters": user_id}}
            )

                # Calculate analytics
        if poll["type"] == "q_and_a":
            total_questions = len(poll.get("questions", []))
            total_answers = sum(len(q.get("answers", [])) for q in poll.get("questions", []))
            analytics_data = {
                "total_questions": total_questions,
                "total_answers": total_answers,
                "questions": poll.get("questions", [])
            }
        else:
            total_votes = sum(poll.get("votes", {}).values())
            analytics_data = {
                "total_votes": total_votes,
                "option_votes": poll.get("votes", {}),
            }

        participation_rate = (
            (len(poll.get("voters", [])) / len(poll.get("participants", []))) * 100
            if poll.get("participants")
            else 0
        )
        voted_users = poll.get("voters", [])
        
        # Fetch feedback for the poll
        feedback = await feedback_collection.find({"poll_id": str(poll_id)}).to_list(length=100)
        logging.debug(f"Poll data for dashboard: {poll}")
        logging.debug(f"Feedback retrieved: {feedback}")
        
        # Render the dashboard template
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "poll_id": poll_id,
                "poll_title": poll.get("activity_title", "Untitled Poll"),
                "poll_question": poll.get("poll_question", ""),
                "total_votes": analytics_data.get("total_votes", 0),
                "total_questions": analytics_data.get("total_questions", 0),
                "total_answers": analytics_data.get("total_answers", 0),
                "participation_rate": participation_rate,
                "option_votes": analytics_data.get("option_votes", {}),
                "voted_users": voted_users,
                "questions": analytics_data.get("questions", []),
                "feedback": feedback,
                "voters": poll.get("voters", []),
                "poll_creator": poll.get("creator"),  # Add this line
                "current_user": current_user
            },
        )

    except Exception as e:
        logging.error(f"Error accessing dashboard for poll ID {poll_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unable to load poll dashboard")
