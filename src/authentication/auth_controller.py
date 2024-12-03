from fastapi import APIRouter, HTTPException, Depends, Response, Request, Form
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from fastapi.responses import RedirectResponse
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
    Ensures the user is added to the database, or raises appropriate errors.
    """
    logging.info(f"Attempting to register user: {username}, {email}")

    # Check if user already exists
    existing_user = await users_collection.find_one({"$or": [{"username": username}, {"email": email}]})
    if existing_user:
        logging.warning(f"User already exists: username={username}, email={email}")
        return RedirectResponse(url="/login?message=Already%20registered", status_code=303)

    # Hash the password
    hashed_password = hash_password(password)

    # User data to insert
    new_user = {
        "username": username,
        "email": email,
        "hashed_password": hashed_password,
        "created_at": datetime.utcnow(),
    }
    logging.debug(f"Inserting new user into the database: {new_user}")

    # Insert user into the database
    try:
        result = await users_collection.insert_one(new_user)
        if not result.inserted_id:
            logging.error("Failed to insert user into the database.")
            raise HTTPException(status_code=500, detail="Failed to register user")
        logging.info(f"User registered successfully: {username}")
    except Exception as e:
        logging.error(f"Database error while registering user: {e}")
        raise HTTPException(status_code=500, detail="An error occurred during registration")

    # Auto-login after successful registration
    token = create_access_token(data={"sub": username})
    response = RedirectResponse(url="/polls", status_code=303)
    response.set_cookie(
        key="Authorization",
        value=f"Bearer {token}",
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return response


@router.post("/login")
async def login_user(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Handles user login.
    Verifies credentials and returns a JWT token.
    """
    logging.info(f"Attempting to log in user: {form_data.username}")

    # Retrieve the user from the database
    try:
        user = await users_collection.find_one({"username": form_data.username})
        if not user:
            logging.warning(f"Login failed: username {form_data.username} not found.")
            raise HTTPException(status_code=400, detail="Invalid credentials")
    except Exception as e:
        logging.error(f"Database error during login for user {form_data.username}: {e}")
        raise HTTPException(status_code=500, detail="An error occurred during login")

    # Verify the password
    if not verify_password(form_data.password, user["hashed_password"]):
        logging.warning(f"Login failed: incorrect password for user {form_data.username}")
        raise HTTPException(status_code=400, detail="Invalid credentials")

    # Generate JWT token
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


async def get_current_user(request: Request):
    """
    Retrieves the authenticated user using the JWT token from the cookies.
    """
    token = request.cookies.get("Authorization")
    if not token or not token.startswith("Bearer "):
        logging.warning("Authentication failed: token missing or invalid.")
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = token[7:]  # Remove "Bearer " prefix
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            logging.error("Invalid token payload: 'sub' is missing.")
            raise HTTPException(status_code=401, detail="Invalid token")

        user = await users_collection.find_one({"username": username})
        if not user:
            logging.warning(f"User not found for token payload: {username}")
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except JWTError as e:
        logging.error(f"JWT decoding error: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")


@router.get("/users/me")
async def read_users_me(current_user: dict = Depends(get_current_user)):
    """
    Retrieves the current authenticated user's information.
    """
    logging.info(f"Fetching data for authenticated user: {current_user['username']}")
    return {"username": current_user["username"], "email": current_user["email"]}
