from fastapi import APIRouter, HTTPException
from src.notifications.fcm_manager import send_notification, subscribe_to_topic
from src.database import device_tokens_collection
from typing import Dict
from datetime import datetime

router = APIRouter()

@router.post("/save-device-token")
async def save_device_token(user_id: str, token: str):
    """
    Saves a device token to the database.
    :param user_id: User identifier.
    :param token: FCM device token.
    """
    if not token:
        raise HTTPException(status_code=400, detail="Device token is required")

    # Check if the token already exists
    existing_token = await device_tokens_collection.find_one({"device_token": token})
    if existing_token:
        return {"message": "Token already exists"}

    # Save the device token to the database
    result = await device_tokens_collection.insert_one({
        "user_id": user_id,
        "device_token": token,
        "created_at": datetime.utcnow()
    })
    return {"message": "Token saved successfully", "token_id": str(result.inserted_id)}

@router.post("/send-notification")
async def send_notification_endpoint(token: str, title: str, body: str):
    """
    Sends a notification to a specific device.
    :param token: FCM device token.
    :param title: Notification title.
    :param body: Notification body.
    """
    try:
        response = await send_notification(token, title, body)
        return {"message": "Notification sent successfully", "response": response}
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/subscribe-to-topic")
async def subscribe_to_topic_endpoint(token: str, topic: str):
    """
    Subscribes a device to a specific topic.
    :param token: FCM device token.
    :param topic: Firebase topic name.
    """
    if not token or not topic:
        raise HTTPException(status_code=400, detail="Token and topic are required")
    try:
        response = await subscribe_to_topic(token, topic)
        return response
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/get-device-tokens/{user_id}")
async def get_device_tokens(user_id: str):
    """
    Retrieves all device tokens for a user.
    :param user_id: User identifier.
    :return: List of device tokens.
    """
    tokens = await device_tokens_collection.find({"user_id": user_id}).to_list(length=100)
    return {"tokens": tokens}
