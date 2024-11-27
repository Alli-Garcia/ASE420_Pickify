# src/authentication/models.py

from pydantic import BaseModel

class User(BaseModel):
    username: str
    password: str  # In a real application, you should hash passwords
    email: str
