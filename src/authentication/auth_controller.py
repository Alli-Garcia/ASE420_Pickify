# src/authentication/auth_controller.py

from fastapi import APIRouter, HTTPException, Depends, Response, Form
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt
from .models import User
from .utils import create_access_token, verify_password, hash_password
from src.database import database
import bcrypt

# Initialize APIRouter for this module
router = APIRouter()

# Secret key and algorithm for JWT (in a real-world scenario, this should be in an environment variable)
SECRET_KEY = "secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# MongoDB collection for users
users_collection = database.get_collection("users")

# OAuth2 Password Bearer token URL (used to fetch the access token)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

@router.post("/register")
async def register_user(
    response: Response,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...)
    ):
    # Check if the username already exists
    existing_user = await users_collection.find_one({"username": username})
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    # Hash the user's password before storing
    hashed_password = hash_password(password)
    user_dict = {
        "username": username,
        "email": email,
        "hashed_password": hashed_password
    }
    
    # Insert the user into the MongoDB collection
    result = await users_collection.insert_one(user_dict)
    
    # Redirect to the polls page after successful registration
    return RedirectResponse(url="/polls", status_code=303)

@router.post("/login")
async def login_user(form_data: OAuth2PasswordRequestForm = Depends()):
    # Fetch the user data from MongoDB collection
    user = await users_collection.find_one({"username": form_data.username})
    if not user or not verify_password(form_data.password, user['hashed_password']):
        raise HTTPException(status_code=400, detail="Invalid username or password")

    # Create a JWT access token for the authenticated user
    access_token = create_access_token(data={"sub": user["username"]})
    response = RedirectResponse(url="/polls", status_code=303)
    response.set_cookie(key="Authorization", value=f"Bearer {access_token}", httponly=True)
    return response

# Utility function to get the current authenticated user using the provided JWT token
async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = await users_collection.find_one({"username": username})
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.get("/users/me")
async def read_users_me(current_user: dict = Depends(get_current_user)):
    # This endpoint retrieves the details of the currently authenticated user
    return {"username": current_user["username"], "email": current_user["email"]}
