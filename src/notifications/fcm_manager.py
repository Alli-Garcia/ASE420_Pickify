from firebase_admin import messaging

async def send_feedback_notification(username: str, poll_title: str):
    # Construct the message
    message = messaging.Message(
        notification=messaging.Notification(
            title="New Feedback Added",
            body=f"{username} added feedback to poll '{poll_title}'"
        ),
        topic="poll-feedback",
    )
    # Send a message to devices subscribed to the provided topic.
    response = messaging.send(message)
    print('Successfully sent message:', response)
