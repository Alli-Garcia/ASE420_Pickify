import matplotlib.pyplot as plt
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import FileResponse, HTMLResponse
from bson import ObjectId
from src.database import database
from src.authentication.auth_controller import get_current_user
from src.shared import templates
import os

router = APIRouter()

# MongoDB Collection
polls_collection = database.get_collection("polls")


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
    # Retrieve the poll
    poll = await polls_collection.find_one({"_id": ObjectId(poll_id)})

    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")

    # Calculate analytics
    total_votes = sum(poll.get("votes", {}).values())
    participation_rate = (
        (len(poll.get("voters", [])) / len(poll.get("participants", []))) * 100
        if poll.get("participants")
        else 0
    )
    option_votes = poll.get("votes", {})
    voted_users = poll.get("voters", [])

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "poll_id": poll_id,
            "poll_title": poll.get("activity_title"),
            "poll_question": poll.get("poll_question", ""),
            "total_votes": total_votes,
            "participation_rate": participation_rate,
            "option_votes": option_votes,
            "voted_users": voted_users,
        },
    )
