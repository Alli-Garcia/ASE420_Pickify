from fastapi import APIRouter, HTTPException, Depends, Response, Request, Form
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt
from src.authentication.utils import create_access_token, verify_password, hash_password, verify_token, initialize_firebase
from src.database import database
import logging
import os
initialize_firebase()
logging.basicConfig(level=logging.DEBUG)

# Initialize APIRouter for this module
router = APIRouter()

# Load secret key and algorithm for JWT
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "default_secret_key")
if SECRET_KEY == "default_secret_key":
    logging.error("JWT_SECRET_KEY is not set in environment variables. Using an insecure default.")
    raise ValueError("JWT_SECRET_KEY must be set in environment variables.")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# MongoDB collection for users
users_collection = database.get_collection("users")

# OAuth2 Password Bearer token URL (used to fetch the access token)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

@router.post("/register")
async def register_user(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...)
):
    """
    Handles user registration.
    - Checks if the username or email already exists.
    - Hashes the password and saves the user to the database.
    """
    logging.info(f"Registering user: {username}, {email}")

    # Check if the username or email already exists
    existing_user = await users_collection.find_one({"$or": [{"username": username}, {"email": email}]})
    if existing_user:
        logging.warning(f"Attempt to register with existing username or email: {username}, {email}")
        return RedirectResponse(
            url="/login?message=Already%20have%20an%20account%3F", status_code=303
        )

    # Hash the user's password before storing
    hashed_password = hash_password(password)
    user_dict = {
        "username": username,
        "email": email,
        "hashed_password": hashed_password,
    }
    result = await users_collection.insert_one(user_dict)

    if not result.inserted_id:
        logging.error("Failed to insert user into the database.")
        raise HTTPException(status_code=500, detail="Failed to create user")

    logging.info(f"User registered successfully: {username}")
    # Automatically log in the user by generating a token
    access_token = create_access_token(data={"sub": username})
    response = RedirectResponse(url="/polls", status_code=303)
    response.set_cookie(
        key="Authorization",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        expires=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        path="/"
    )
    return response


@router.post("/login")
async def login_user(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await users_collection.find_one({"username": form_data.username})
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": user["username"]})
    response = RedirectResponse(url="/polls", status_code=303)
    response.set_cookie(
        key="Authorization",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    return response

async def get_current_user(request: Request):
    """
    Retrieves the current authenticated user using the JWT token in cookies.
    """
    token = request.cookies.get("Authorization")
    if token and token.startswith("Bearer "):
        token = token[7:]  # Remove the "Bearer " prefix

    logging.debug(f"Token retrieved from cookie: {token}")

    if not token:
        logging.error("Authentication token not found in cookies.")
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            logging.error("Invalid token payload: missing 'sub'.")
            raise HTTPException(status_code=401, detail="Invalid token")

        user = await users_collection.find_one({"username": username})
        if user is None:
            logging.warning(f"User not found for token payload: {username}")
            raise HTTPException(status_code=401, detail="User not found")

        logging.info(f"Authenticated user: {username}")
        return user
    except JWTError as e:
        logging.error(f"JWT decoding error: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")


@router.get("/users/me")
async def read_users_me(current_user: dict = Depends(get_current_user)):
    """
    Retrieves the details of the currently authenticated user.
    """
    return {"username": current_user["username"], "email": current_user["email"]}
