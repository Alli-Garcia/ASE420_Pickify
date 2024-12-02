from datetime import datetime, timedelta, timezone
from typing import Union, List
from jose import jwt, JWTError
import bcrypt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from firebase_admin import credentials, initialize_app
import firebase_admin
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

from dotenv import load_dotenv
load_dotenv()

# Validate environment variables
required_env_vars = ["SECRET_KEY", "FIREBASE_ADMIN_JSON", "SMTP_SERVER", "SMTP_PORT", "EMAIL_ADDRESS", "EMAIL_PASSWORD"]
missing_env_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_env_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_env_vars)}")

# Load environment variables
SECRET_KEY = os.getenv("SECRET_KEY", "default_secret_key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
firebase_json_path = os.getenv("FIREBASE_ADMIN_JSON")
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT"))
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

# Firebase Initialization
def initialize_firebase():
    if not firebase_admin._apps:
        cred = credentials.Certificate(firebase_json_path)
        initialize_app(cred)

# OAuth2 password bearer token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# JWT Token Functions
def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None):
    to_encode = data.copy()
    if "sub" not in to_encode:
        raise ValueError("Missing `sub` key in token data.")
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token: Missing 'sub' claim.")
        return username
    except JWTError as e:
        logging.error(f"Token verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    return verify_token(token)

# Password Functions
def hash_password(password: str) -> str:
    logging.debug("Hashing password")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    result = bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    logging.debug(f"Password verification result: {result}")
    return result

# Email Sending
def send_email(recipients: List[str], subject: str, body: str):
    logging.info(f"Attempting to send email to: {recipients}")
    try:
        # Setup SMTP server connection
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        logging.info("SMTP server login successful")

        # Create and send the email
        message = MIMEMultipart()
        message["From"] = EMAIL_ADDRESS
        message["To"] = ", ".join(recipients)
        message["Subject"] = subject
        message.attach(MIMEText(body, "plain"))
        server.sendmail(EMAIL_ADDRESS, recipients, message.as_string())
        server.quit()
        logging.info("Email sent successfully")
    except Exception as e:
        logging.error(f"Error sending email: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send email: {e}")
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    email_address = os.getenv("EMAIL_ADDRESS")
    email_password = os.getenv("EMAIL_PASSWORD")

    if not smtp_server or not email_address or not email_password:
        raise Exception("SMTP configuration is missing in environment variables")

    try:
        # Set up the SMTP server
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(email_address, email_password)

        # Create the email
        message = MIMEMultipart()
        message["From"] = email_address
        message["To"] = ", ".join(recipients)
        message["Subject"] = subject
        message.attach(MIMEText(body, "plain"))

        # Send the email
        server.sendmail(email_address, recipients, message.as_string())
        server.quit()
        print(f"Email sent successfully to: {recipients}")
    except Exception as e:
        print(f"Failed to send email: {e}")
        raise