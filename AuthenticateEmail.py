import os
import time
import base64
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from instagram_downloader import download_instagram_reel  # Import new function
from gmail_cleanup_new import authenticate_gmail, delete_emails

load_dotenv()  # Load environment variables from .env file

title_club_mars = True

from YoutubeUpload import (  
    upload_video,
    authenticate_youtube,
    #generate_description,
    read_last_upload_time,
    write_last_upload_time,
    calculate_next_upload_time, ) # Import YouTube upload functions


# Define the scope for Gmail API
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']  # Changed scope to allow modifications

def authenticate_gmail():
    """Authenticate with Gmail API and return the service object."""
    try:
        # Use the token manager to get an authenticated service
        from token_manager import get_gmail_service
        return get_gmail_service(full_access=False)
    except Exception as e:
        print(f"Error authenticating Gmail: {e}")
        # Fallback to legacy authentication if the token manager fails
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

        # Extract subject
        subject = ""
        for header in headers:
            if header['name'] == 'Subject':
                subject = header['value']

        # Set default if subject is missing or empty
        if title_club_mars or not subject:
            subject = "#MilanaKateryna"
            
        # Extract body
        body = ""
        if 'data' in payload['body']:
            body = base64.urlsafe_b64decode(payload['body']['data']).decode()
        elif 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == "text/plain" and 'data' in part['body']:
                    body = base64.urlsafe_b64decode(part['body']['data']).decode()
                elif part['mimeType'] == "text/html" and 'data' in part['body']:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(base64.urlsafe_b64decode(part['body']['data']).decode(), 'html.parser')
                    links = soup.find_all('a')
                    for link in links:
                        if 'instagram.com' in link.get('href', ''):
                            body = link.get('href')
                            break

        # Mark as read
        service.users().messages().modify(userId='me', id=msg_id, body={"removeLabelIds": ["UNREAD"]}).execute()

        return subject, body

def process_email(subject, body, youtube):
    """Extract Instagram URL, download the video, and upload it to YouTube."""
    if body and body.startswith("https://www.instagram.com"):
        print(f"Downloading video from: {body}")
        
        # Use the custom_filename parameter to download directly with the subject name
        downloads_folder = r"C:\Users\super\Downloads"
        
        # Download with custom filename directly - no renaming needed
        downloaded_path = download_instagram_reel(body, downloads_folder, subject)
        
        if downloaded_path:
            print(f"Downloaded video saved as: {downloaded_path}")
            
            # Generate description
            #description = generate_description(subject)
            #description += " funny memes shorts fyp memes I found on discord discord memes daily memes"
            description = "subscribe! MilanaKateryna"
            # Define tags
            tags = ["clubmarslive", "clubmars","shorts", "#hot","fyp", "viral"]
                    # "funny", "trending", "entertainment", "dailymemes", "nostalgia",
                   #"nostalgic", "relatable", "memories", "viralvideos", "virallibrary", "memehistory", "viralhistory", "funnyshorts",
                   #"lmao","memorablevideos", "caughtoncamera", "funnycontent", "dailycomedy", "funnyvideo"]
            
            playlist_name = "funny memes shorts compilation"
            
            # Read last upload time from file
            last_upload_time = read_last_upload_time()
            
            # Schedule next upload time using ONLY the file data
            next_upload_time = calculate_next_upload_time(youtube, last_upload_time, check_youtube_api=False)
            
            # Double-check that the upload time is valid (at least 15 mins in future)
            local_tz = datetime.now().astimezone().tzinfo
            now = datetime.now(local_tz)
            now_utc = now.astimezone(timezone.utc)
            
            if next_upload_time <= now_utc + timedelta(minutes=15):
                print(f"Warning: Calculated upload time {next_upload_time} is too soon. Adjusting...")
                # Use a fallback time 20 minutes from now
                fallback_time = now + timedelta(minutes=20)
                next_upload_time = fallback_time.astimezone(timezone.utc)
                print(f"Using fallback time: {fallback_time}")
            
            # Upload video to YouTube
            upload_video(youtube, downloaded_path, subject, description, tags, next_upload_time, playlist_name)
            
            # Update the last upload time - IMPORTANT: store in local time for readability
            next_local_time = next_upload_time.astimezone(local_tz)
            write_last_upload_time(next_local_time)
            
            print("Video uploaded successfully!")
        else:
            print("Failed to download Instagram video.")
    else:
        print("No valid Instagram URL found in the email body.")
        
def main():
    counter = 0
    sender_email = os.getenv("SENDER_EMAIL")  # Use the environment variable from .env file
    gmail_service = authenticate_gmail()
    youtube_service = authenticate_youtube()  # Authenticate YouTube service
    
    # Read local last upload time
    last_upload_time = read_last_upload_time()
    if last_upload_time:
        print(f"Initial last upload time from file: {last_upload_time}")
    else:
        print("No previous upload time found in file.")
    
    print("Monitoring for emails...")

    while True:
        subject, body = check_email(gmail_service, sender_email)
        if subject and body:
            print(f"New Email Received - Subject: {subject}")
            process_email(subject, body, youtube_service)
        time.sleep(10)  # Check every 10 seconds
        
if __name__ == '__main__':
    main()