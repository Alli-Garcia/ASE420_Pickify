import matplotlib.pyplot as plt
from fastapi import APIRouter, HTTPException, Form
from fastapi.responses import FileResponse
from src.database import database
from bson import ObjectId
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
    plt.bar(options, votes)
    plt.xlabel('Options')
    plt.ylabel('Votes')
    plt.title(f'Results for Poll: {poll["activity_title"]}')
    plt.xticks(rotation=45, ha="right")  # Rotate the x-axis labels if needed

    # Define the file path for saving the report
    report_filename = f"{poll_id}_report.png"
    plt.tight_layout()  # Adjust the layout for better spacing
    plt.savefig(report_filename)
    plt.close()  # Close the plot to release memory

    # Return the report as a downloadable file
    return FileResponse(path=report_filename, media_type="image/png", filename=report_filename)
