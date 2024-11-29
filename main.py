# main.py

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from src.authentication.auth_controller import router as auth_router
from src.polls.poll_controller import router as poll_router
from src.feedback.feedback_controller import router as feedback_router
from src.voting.voting_controller import router as voting_router
from fastapi import WebSocket, WebSocketDisconnect, StaticFiles
from pathlib import Path
from src.websockets.connection_manager import ConnectionManager
from typing import List

# Create an instance of FastAPI
app = FastAPI()
manager = ConnectionManager()

static_path = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_path), name="static")

# Register routers from different modules
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(poll_router, prefix="/polls", tags=["Polls"])
app.include_router(feedback_router, prefix="/feedback", tags=["Feedback"])
app.include_router(voting_router, prefix="/voting", tags=["Voting"])

# Root endpoint for testing
@app.get("/")
async def root():
    return {"message": "Welcome to Pickify!"}

@app.websocket("/ws/polls/{poll_id}")
async def websocket_endpoint(websocket: WebSocket, poll_id: str):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()  # Clients can also send data if needed
            await manager.broadcast(f"Poll {poll_id} update: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/", response_class=HTMLResponse)
async def read_root():
    return app.get_template("index.html")

@app.get("/login", response_class=HTMLResponse)
async def read_login():
    return app.get_template("login.html")

@app.get("/register", response_class=HTMLResponse)
async def read_register():
    return app.get_template("register.html")

@app.get("/polls", response_class=HTMLResponse)
async def read_polls():
    return app.get_template("polls.html")

@app.get("/feedback", response_class=HTMLResponse)
async def read_feedback():
    return app.get_template("feedback.html")