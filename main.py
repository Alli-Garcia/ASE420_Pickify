# main.py

from fastapi import FastAPI
from src.authentication.auth_controller import router as auth_router
from src.polls.poll_controller import router as poll_router
from src.feedback.feedback_controller import router as feedback_router
from src.voting.voting_controller import router as voting_router

# Create an instance of FastAPI
app = FastAPI()

# Register routers from different modules
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(poll_router, prefix="/polls", tags=["Polls"])
app.include_router(feedback_router, prefix="/feedback", tags=["Feedback"])
app.include_router(voting_router, prefix="/voting", tags=["Voting"])

# Root endpoint for testing
@app.get("/")
async def root():
    return {"message": "Welcome to Pickify!"}

