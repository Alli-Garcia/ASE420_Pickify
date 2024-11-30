from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from motor.motor_asyncio import AsyncIOMotorClient
from starlette.staticfiles import StaticFiles
from src.authentication.auth_controller import router as auth_router
from src.polls.poll_controller import router as poll_router
from src.feedback.feedback_controller import router as feedback_router
from src.voting.voting_controller import router as voting_router
from src.websockets.connection_manager import ConnectionManager
from pathlib import Path
import logging

# Create an instance of FastAPI
app = FastAPI()
manager = ConnectionManager()
logging.basicConfig(level=logging.DEBUG)
# MongoDB connection setup
MONGODB_URI = "mongodb://localhost:27017/"
client = AsyncIOMotorClient(MONGODB_URI)
database = client.get_database("pickify_db")
users_collection = database.get_collection("users")

# Static files setup
static_path = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_path), name="static")
templates = Jinja2Templates(directory=str(static_path))

# Register routers from different modules
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(poll_router, prefix="/polls", tags=["Polls"])
app.include_router(feedback_router, prefix="/feedback", tags=["Feedback"])
app.include_router(voting_router, prefix="/voting", tags=["Voting"])

# Root endpoint for serving index.html
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# WebSocket endpoint for poll updates
@app.websocket("/ws/polls/{poll_id}")
async def websocket_endpoint(websocket: WebSocket, poll_id: str):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(f"Poll {poll_id} update: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logging.info(f"Client disconnected from poll {poll_id}")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")

# Other endpoints for serving HTML pages
@app.get("/login", response_class=HTMLResponse)
async def read_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def read_register(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/polls", response_class=HTMLResponse)
async def read_polls(request: Request):
    return templates.TemplateResponse("polls.html", {"request": request})

@app.get("/feedback", response_class=HTMLResponse)
async def read_feedback(request: Request):
    return templates.TemplateResponse("feedback.html", {"request": request})

@app.get("/analytics/{poll_id}", response_class=HTMLResponse)
async def analytics_dashboard(request: Request, poll_id: str):
    return templates.TemplateResponse("dashboard.html", {"request": request, "poll_id": poll_id})
