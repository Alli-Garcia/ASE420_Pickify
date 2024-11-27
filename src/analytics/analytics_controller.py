import matplotlib.pyplot as plt
from fastapi import APIRouter

router = APIRouter()

@router.get("/report/{poll_title}")
async def poll_report(poll_title: str):
    for poll in poll_db:
        if poll.title == poll_title:
            # Generate bar chart of poll results
            options = list(poll.votes.keys())
            votes = list(poll.votes.values())

            plt.bar(options, votes)
            plt.xlabel('Options')
            plt.ylabel('Votes')
            plt.title(f'Results for Poll: {poll_title}')
            plt.savefig(f"{poll_title}_report.png")
            return {"message": f"Report generated: {poll_title}_report.png"}
    raise HTTPException(status_code=404, detail="Poll not found")
