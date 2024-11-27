# src/authentication/auth_controller.py

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from datetime import timedelta
from typing import Optional
from jose import JWTError, jwt
from .models import User
from .utils import create_access_token
import bcrypt

# Initialize APIRouter for this module
router = APIRouter()

# Secret key and algorithm for JWT (in a real-world scenario, this should be in an environment variable)
SECRET_KEY = "secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Temporary in-memory user store
user_db = {}

# OAuth2 Password Bearer token URL (used to fetch the access token)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


@router.post("/register")
async def register_user(user: User):
    # Check if the username already exists
    if user.username in user_db:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Hash the user's password before storing
    hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt())
    user_db[user.username] = {
        "username": user.username,
        "email": user.email,
        "password": hashed_password  # Store the hashed password
    }
    return {"message": "User registered successfully"}


@router.post("/login")
async def login_user(form_data: OAuth2PasswordRequestForm = Depends()):
    # Fetch the user data from in-memory user_db
    user = user_db.get(form_data.username)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid username or password")

    # Verify hashed password
    if not bcrypt.checkpw(form_data.password.encode('utf-8'), user['password']):
        raise HTTPException(status_code=400, detail="Invalid username or password")

    # Create a JWT access token for the authenticated user
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


# Utility function to get the current authenticated user using the provided JWT token
async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = user_db.get(username)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@router.get("/users/me")
async def read_users_me(current_user: dict = Depends(get_current_user)):
    # This endpoint retrieves the details of the currently authenticated user
    return {"username": current_user["username"], "email": current_user["email"]}
