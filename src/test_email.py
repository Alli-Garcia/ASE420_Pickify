import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = "alligarcia2021@gmail.com"
EMAIL_PASSWORD = "ehpl ejvr wvzu terg"  # Replace with your App Password

def test_email():
    try:
        # Set up the SMTP connection
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.set_debuglevel(1)  # Enable detailed debug output
        server.starttls()  # Start TLS encryption
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        print("SMTP connection and login successful!")

        # Create the email
        recipients = ["alligarcia2025@gmail.com"]  # Replace with your test email
        message = MIMEMultipart()
        message["From"] = EMAIL_ADDRESS
        message["To"] = ", ".join(recipients)
        message["Subject"] = "Test Email"
        message.attach(MIMEText("This is a test email sent from Python.", "plain"))

        # Send the email
        server.sendmail(EMAIL_ADDRESS, recipients, message.as_string())
        print("Email sent successfully!")

        # Close the server connection
        server.quit()

    except Exception as e:
        print(f"Failed to send email: {e}")

test_email()
