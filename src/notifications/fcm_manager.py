import firebase_admin
from firebase_admin import credentials, messaging
__all__ = ["send_notification_to_device", "send_notification_to_topic", "send_feedback_notification"]

# Firebase Admin SDK Initialization (Singleton)
if not firebase_admin._apps:
    cred = credentials.Certificate("config/firebase-adminsdk.json")  # Replace with your service account JSON path
    firebase_admin.initialize_app(cred)

async def send_notification(device_token: str, title: str, body: str):
    """
    Sends a notification to a specific device using Firebase Cloud Messaging.
    :param device_token: The FCM token of the target device.
    :param title: Notification title.
    :param body: Notification body.
    :return: The Firebase response.
    """
    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        token=device_token,
    )
    try:
        response = messaging.send(message)
        return {"message": "Successfully sent message", "response_id": response}
    except messaging.FirebaseError as e:
        raise ValueError(f"Firebase error: {e}")
    except Exception as e:
        raise ValueError(f"An error occurred while sending the notification: {e}")

def send_feedback_notification(device_token, title, body):
    """
    Sends a feedback notification to a specific device.
    :param device_token: The FCM token of the device.
    :param title: The title of the notification.
    :param body: The body of the notification.
    """
    from firebase_admin import messaging

    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        token=device_token,
    )
    try:
        response = messaging.send(message)
        print(f"Successfully sent feedback notification: {response}")
    except Exception as e:
        print(f"Error sending feedback notification: {e}")
        raise e


async def subscribe_to_topic(device_token: str, topic: str):
    """
    Subscribes a device to a topic.
    :param device_token: The FCM token of the target device.
    :param topic: The topic name to subscribe to.
    :return: Firebase response.
    """
    try:
        response = messaging.subscribe_to_topic([device_token], topic)
        return {"message": f"Successfully subscribed to topic {topic}", "response": response}
    except messaging.FirebaseError as e:
        raise ValueError(f"Firebase error: {e}")
    except Exception as e:
        raise ValueError(f"An error occurred while subscribing to topic: {e}")
