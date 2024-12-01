from datetime import datetime, timedelta, timezone
from typing import Union, List
from jose import jwt, JWTError
import bcrypt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

# Load environment variables or set defaults
SECRET_KEY = os.getenv("SECRET_KEY", "default_secret_key")  # Fallback to "default_secret_key" if not set
if SECRET_KEY == "default_secret_key":
    logging.warning("SECRET_KEY is not set in the environment. Using a default insecure key.")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# Email Configuration (set in your environment)
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "your_email@example.com")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "your_password")

# OAuth2 password bearer token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# Function to create a JWT token
def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None):
    to_encode = data.copy()
    if "sub" not in to_encode:
        raise ValueError("Missing `sub` key in token data.")
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Function to verify a JWT token
def verify_token(token: str) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise JWTError("Invalid token: Missing `sub` claim.")
        return username
    except JWTError as e:
        logging.error(f"Token verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")

# Function to retrieve the current user
async def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    return verify_token(token)

# Function to hash a password
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")

# Function to verify a password against a hashed password
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

# Function to send an email
def send_email(recipients: List[str], subject: str, body: str):
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        raise HTTPException(status_code=500, detail="Email configuration is missing")
    
    try:
        # Set up the email server
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()  # Upgrade connection to secure
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)

        # Construct the email
        message = MIMEMultipart()
        message["From"] = EMAIL_ADDRESS
        message["To"] = ", ".join(recipients)
        message["Subject"] = subject
        message.attach(MIMEText(body, "plain"))

        # Send the email
        server.sendmail(EMAIL_ADDRESS, recipients, message.as_string())
        server.quit()
        logging.info(f"Email sent successfully to: {recipients}")
    except Exception as e:
        logging.error(f"Failed to send email: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send email: {e}")
