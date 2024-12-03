from fastapi import APIRouter, HTTPException, Depends, Response, Request, Form
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from fastapi.responses import RedirectResponse
from datetime import datetime, timezone
from jose import JWTError, jwt
from src.authentication.utils import create_access_token, verify_password, hash_password, initialize_firebase
from src.database import users_collection
import logging
import os

# Initialize Firebase Admin SDK
initialize_firebase()

# Logging setup
logging.basicConfig(level=logging.DEBUG)

# JWT configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "default_secret_key")
if SECRET_KEY == "default_secret_key":
    logging.warning("Using default secret key. This is insecure.")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Initialize FastAPI router
router = APIRouter()

# OAuth2 token scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


@router.post("/register")
async def register_user(username: str = Form(...), email: str = Form(...), password: str = Form(...)):
    """
    Handles user registration.
    Ensures the user is added to the database or raises appropriate errors.
    """
    logging.info(f"Attempting to register user: username={username}, email={email}")

    try:
        # Check if the user already exists
        existing_user = await users_collection.find_one({"$or": [{"username": username}, {"email": email}]})
        if existing_user:
            logging.warning(f"User already exists: username={username}, email={email}")
            return RedirectResponse(url="/login?message=Already%20registered", status_code=303)

        # Hash the password
        hashed_password = hash_password(password)
        logging.debug(f"Hashed password: {hashed_password}")

        # Prepare user data
        new_user = {
            "username": username,
            "email": email,
            "hashed_password": hashed_password,
            "created_at": datetime.now(timezone.utc),
        }
        logging.debug(f"Prepared user data for insertion: {new_user}")

        # Insert the user into the database
        result = await users_collection.insert_one(new_user)
        logging.debug(f"Insert operation result: {result.inserted_id}")
        if not result.inserted_id:
            raise ValueError("Insert operation returned no ID.")

        logging.info(f"User registered successfully: username={username}")

        # Generate and return JWT token
        token = create_access_token(data={"sub": username})
        response = RedirectResponse(url="/polls", status_code=303)
        response.set_cookie(
            key="Authorization",
            value=f"Bearer {token}",
            httponly=True,
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
        return response

    except Exception as e:
        logging.error(f"Error during registration: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred during registration")


@router.post("/login")
async def login_user(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Handles user login.
    Verifies credentials and returns a JWT token.
    """
    logging.info(f"Attempting to log in user: username={form_data.username}")

    try:
        # Retrieve the user from the database
        user = await users_collection.find_one({"username": form_data.username})
        if not user:
            logging.warning(f"Login failed: username={form_data.username} not found.")
            raise HTTPException(status_code=400, detail="Invalid credentials")

        # Verify the password
        if not verify_password(form_data.password, user["hashed_password"]):
            logging.warning(f"Login failed: incorrect password for user {form_data.username}")
            raise HTTPException(status_code=400, detail="Invalid credentials")

        # Generate and return JWT token
        token = create_access_token(data={"sub": user["username"]})
        response = RedirectResponse(url="/polls", status_code=303)
        response.set_cookie(
            key="Authorization",
            value=f"Bearer {token}",
            httponly=True,
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
        logging.info(f"User logged in successfully: {form_data.username}")
        return response

    except Exception as e:
        logging.error(f"Error during login for user {form_data.username}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred during login")


async def get_current_user(request: Request):
    """
    Retrieves the authenticated user using the JWT token from the cookies.
    """
    token = request.cookies.get("Authorization")
    if not token or not token.startswith("Bearer "):
        logging.warning("Authentication failed: token missing or invalid.")
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        # Decode and validate the token
        token = token[7:]  # Remove "Bearer " prefix
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token: Missing 'sub' claim.")

        # Retrieve the user from the database
        user = await users_collection.find_one({"username": username})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user

    except JWTError as e:
        logging.error(f"JWT decoding error: {e}", exc_info=True)
        raise HTTPException(status_code=401, detail="Invalid token")


@router.get("/users/me")
async def read_users_me(current_user: dict = Depends(get_current_user)):
    """
    Retrieves the current authenticated user's information.
    """
    logging.info(f"Fetching data for authenticated user: {current_user['username']}")
    return {"username": current_user["username"], "email": current_user["email"]}
