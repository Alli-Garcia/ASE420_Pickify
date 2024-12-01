from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.responses import HTMLResponse
from starlette.staticfiles import StaticFiles
from jose import JWTError, jwt
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from firebase_admin import initialize_app, credentials
from bson import ObjectId
from dotenv import load_dotenv
import logging
import json
import os

# Load environment variables
load_dotenv()
print("MONGODB_USERNAME:", os.getenv("MONGODB_USERNAME"))
print("MONGODB_PASSWORD:", os.getenv("MONGODB_PASSWORD"))
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "default_secret_key")
ALGORITHM = "HS256"
if SECRET_KEY == "default_secret_key":
    raise ValueError("JWT_SECRET_KEY is not set in environment variables.")  # Use a fallback for safety

firebase_json_path = os.getenv("FIREBASE_ADMIN_JSON")
if not firebase_json_path:
    raise ValueError(f"Firebase Admin JSON path is missing or invalid: {firebase_json_path}")

with open(firebase_json_path, "r") as f:
    firebase_json = json.load(f)

# Initialize Firebase Admin SDK
cred = credentials.Certificate(firebase_json)
initialize_app(cred)

# Import routers from their respective modules
from src.authentication.auth_controller import router as auth_router, get_current_user
from src.notifications.fcm_controller import router as fcm_router
from src.polls.poll_controller import router as poll_router
from src.feedback.feedback_controller import router as feedback_router
from src.voting.voting_controller import router as voting_router
from src.shared import templates, polls_collection
from src.websockets.connection_manager import ConnectionManager

# Create an instance of FastAPI
app = FastAPI()
manager = ConnectionManager()
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Replace with your frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    # Skip authentication for specific endpoints like /register and /login
    public_routes = ["/auth/register", "/auth/login", "/", "/static"]
    if any(request.url.path.startswith(route) for route in public_routes):
        return await call_next(request)

    # Enforce authentication for other routes
    token = request.cookies.get("Authorization")
    if not token or not token.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        # Validate the token
        token = token[7:]  # Remove "Bearer " prefix
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    return await call_next(request)

# Static Files and Templates Setup
static_path = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_path), name="static")

# Register routers from different modules
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(poll_router, prefix="/polls", tags=["Polls"])
app.include_router(feedback_router, prefix="/feedback", tags=["Feedback"])
app.include_router(voting_router, prefix="/voting", tags=["Voting"])
app.include_router(fcm_router, prefix="/fcm", tags=["FCM"])

# Root endpoint for serving index.html
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# WebSocket endpoint for poll updates
@app.websocket("/ws/polls/{poll_id}")
async def websocket_endpoint(websocket: WebSocket, poll_id: str):
    await manager.connect(websocket)
    logging.info(f"Client connected to poll {poll_id}")
    try:
        while True:
            data = await websocket.receive_text()
            logging.debug(f"Received data: {data}")
            await manager.broadcast(f"Poll {poll_id} update: {data}")
    except WebSocketDisconnect:
        logging.info(f"Client disconnected from poll {poll_id}")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
    finally:
        manager.disconnect(websocket)

# Other endpoints for serving HTML pages
@app.get("/login", response_class=HTMLResponse)
async def read_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def read_register(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/polls", response_class=HTMLResponse)
async def read_polls(request: Request, current_user: dict = Depends(get_current_user)):
    try:
        polls_cursor = polls_collection.find({})
        polls = await polls_cursor.to_list(length=100)
        logging.debug(f"Polls retrieved: {polls}")
    except Exception as e:
        logging.error(f"Error fetching polls: {e}")
        raise HTTPException(status_code=500, detail="Unable to fetch polls at this time")

    return templates.TemplateResponse("polls.html", {"request": request, "polls": polls, "current_user": current_user})

@app.get("/feedback", response_class=HTMLResponse)
async def read_feedback(request: Request):
    return templates.TemplateResponse("feedback.html", {"request": request})

@app.get("/analytics/{poll_id}", response_class=HTMLResponse)
async def analytics_dashboard(request: Request, poll_id: str, current_user: dict = Depends(get_current_user)):
    poll = await polls_collection.find_one({"_id": ObjectId(poll_id)})
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "poll_id": str(poll["_id"]),
        "poll_title": poll["activity_title"],
        "poll_question": poll["poll_question"],
        "total_participants": len(poll.get("participants", [])),
        "votes": poll.get("votes", {}),
    })
