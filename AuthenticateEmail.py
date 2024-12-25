import os
import time
import base64
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from IGvideodownload import get_video_url, download_video  # Import functions from IGvideodownload.py

# Define the scope for Gmail API
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def authenticate_gmail():
    """Authenticate with Gmail API and return the service object."""
    creds = None
    if os.path.exists('token.json'):
        from google.oauth2.credentials import Credentials
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)

def check_email(service, sender_email):
    """Check for new emails from a specific sender."""
    results = service.users().messages().list(userId='me', q=f'from:{sender_email} is:unread').execute()
    messages = results.get('messages', [])
    if not messages:
        print("No new emails.")
        return None, None
    else:
        msg_id = messages[0]['id']
        message = service.users().messages().get(userId='me', id=msg_id).execute()
        payload = message['payload']
        headers = payload['headers']
        subject = ""
        for header in headers:
            if header['name'] == 'Subject':
                subject = header['value']
        # Decode the email body
        body = ""
        if 'data' in payload['body']:
            body = base64.urlsafe_b64decode(payload['body']['data']).decode()
        elif 'parts' in payload:
            for part in payload['parts']:
                if 'data' in part['body']:
                    body = base64.urlsafe_b64decode(part['body']['data']).decode()
        return subject, body

def process_email(subject, body):
    """Extract Instagram URL and download the video."""
    instagram_url = body.strip()  # Assuming the body contains only the Instagram URL
    if instagram_url.startswith("https://www.instagram.com"):
        print(f"Downloading video from: {instagram_url}")
        video_url = get_video_url(instagram_url)
        if video_url:
            download_video(video_url, f"{subject}.mp4")
        else:
            print("Failed to extract video URL.")
    else:
        print("No valid Instagram URL found in the email body.")

def main():
    sender_email = "YOUREMAILHERE"
    service = authenticate_gmail()
    print("Monitoring for emails...")

    processed_emails = set()  # Track processed email IDs to avoid reprocessing

    while True:
        subject, body = check_email(service, sender_email)
        if subject and body:
            print(f"New Email Received - Subject: {subject}")
            process_email(subject, body)
        time.sleep(10)  # Check every 10 seconds

if __name__ == '__main__':
    main()
