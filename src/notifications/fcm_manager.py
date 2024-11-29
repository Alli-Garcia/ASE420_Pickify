from firebase_admin import messaging
import logging

logging.basicConfig(level=logging.INFO)

# General function to send FCM notification to a specific topic
def send_notification(topic: str, title: str, body: str):
    # Construct the message
    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body
        ),
        topic=topic,
    )
    try:
        # Send the message to devices subscribed to the provided topic
        response = messaging.send(message)
        logging.info(f'Successfully sent message to topic "{topic}": {response}')
    except Exception as e:
        logging.error(f"Failed to send message to topic '{topic}': {e}")
# Function specifically to send feedback notifications
def send_feedback_notification(username: str, poll_title: str, poll_id: str):
    # Construct the message for feedback notification
    message = messaging.Message(
        notification=messaging.Notification(
            title="New Feedback Added",
            body=f"{username} added feedback to poll '{poll_title}'"
        ),
        topic=f"poll-{poll_id}",
    )
    try:
        # Send a message to devices subscribed to the provided topic
        response = messaging.send(message)
        logging.info(f'Successfully sent feedback notification to topic "poll-{poll_id}": {response}')
    except Exception as e:
        logging.error(f"Failed to send feedback notification: {e}")