# main.py

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from pathlib import Path
from src.authentication.auth_controller import router as auth_router
from src.polls.poll_controller import router as poll_router
from src.feedback.feedback_controller import router as feedback_router
from src.voting.voting_controller import router as voting_router
from fastapi import WebSocket, WebSocketDisconnect
from src.websockets.connection_manager import ConnectionManager
from typing import List
from motor.motor_asyncio import AsyncIOMotorClient
from starlette.staticfiles import StaticFiles


# Create an instance of FastAPI
app = FastAPI()
manager = ConnectionManager()

MONGODB_URI = "mongodb://localhost:27017/"
client = AsyncIOMotorClient(MONGODB_URI)

database = client.get_database("pickify_db")

users_collection = database.get_collection("users")

static_path = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_path), name="static")

# Register routers from different modules
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(poll_router, prefix="/polls", tags=["Polls"])
app.include_router(feedback_router, prefix="/feedback", tags=["Feedback"])
app.include_router(voting_router, prefix="/voting", tags=["Voting"])

# Root endpoint for testing
@app.get("/", response_class=HTMLResponse)
async def read_root():
    index_path = static_path / "index.html"
    with open(index_path, "r") as file:
        html_content = file.read()
    return HTMLResponse(content=html_content)

@app.websocket("/ws/polls/{poll_id}")
async def websocket_endpoint(websocket: WebSocket, poll_id: str):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()  # Clients can also send data if needed
            await manager.broadcast(f"Poll {poll_id} update: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/login", response_class=HTMLResponse)
async def read_login():
    login_path = static_path / "login.html"
    with open(login_path, "r") as file:
        html_content = file.read()
    return HTMLResponse(content=html_content)

@app.get("/register", response_class=HTMLResponse)
async def read_register():
    register_path = static_path / "register.html"
    with open(register_path, "r") as file:
        html_content = file.read()
    return HTMLResponse(content=html_content)

@app.get("/polls", response_class=HTMLResponse)
async def read_polls():
    polls_path = static_path / "polls.html"
    with open(polls_path, "r") as file:
        html_content = file.read()
    return HTMLResponse(content=html_content)

@app.get("/feedback", response_class=HTMLResponse)
async def read_feedback():
    feedback_path = static_path / "feedback.html"
    with open(feedback_path, "r") as file:
        html_content = file.read()
    return HTMLResponse(content=html_content)

@app.get("/analytics/{poll_id}", response_class=HTMLResponse)
async def analytics_dashboard(poll_id: str):
    file_path = static_path / "dashboard.html"
    with open(file_path, 'r', encoding='utf-8') as file:
        html_content = file.read()
    return HTMLResponse(content=html_content)