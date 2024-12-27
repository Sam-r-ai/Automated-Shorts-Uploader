import os
import time
import base64
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from IGvideodownload import get_video_url, download_video  # Import functions from IGvideodownload.py
from YoutubeUpload import (  
    upload_video,
    authenticate_youtube,
    generate_description,
    read_last_upload_time,
    write_last_upload_time,
    calculate_next_upload_time, ) # Import YouTube upload functions


# Define the scope for Gmail API
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']  # Changed scope to allow modifications

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

        # Extract subject
        subject = ""
        for header in headers:
            if header['name'] == 'Subject':
                subject = header['value']

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
        video_url = get_video_url(body)
        if video_url:
            file_name = f"{subject}.mp4"
            download_video(video_url, file_name)
            print(f"Downloaded video saved as: {file_name}")

            file_location = rf"C:\Users\super\Downloads\{file_name}"
            # Generate description
            description = generate_description(subject)

            # Define tags
            tags = ["Shorts", "Viral", "fyp", "memes", "Funny", "Trending", "Entertainment", "FYP", "dailymemes", "Comedy",
            "humor", "relatable", "hilarious", "LOL", "Jokes", "LaughOutLoud", "FunnyVideo", "skit", "funnyshorts",
            "ComedyShorts", "ViralComedy", "funnycontent", "dailycomedy", "funnyvideo"]
            playlist_name = "memes"
            # Read last upload time
            last_upload_time = read_last_upload_time()
            print(f"last upload time: {last_upload_time}")
            # Schedule next upload time
            next_upload_time = calculate_next_upload_time(last_upload_time)
            next_upload_time_iso = next_upload_time.isoformat().replace("+00:00", "Z")
            print(f"Scheduled upload time: {next_upload_time_iso}")
            # Upload video to YouTube
            upload_video(youtube, file_location, subject, description, tags, next_upload_time_iso, playlist_name)

            # Update last upload time
            write_last_upload_time(next_upload_time)
            print("Video uploaded successfully!")
        else:
            print("Failed to extract video URL.")
    else:
        print("No valid Instagram URL found in the email body.")

def main():
    sender_email = "justinferrari91@gmail.com"
    gmail_service = authenticate_gmail()
    youtube_service = authenticate_youtube()  # Authenticate YouTube service
    print("Monitoring for emails...")

    while True:
        subject, body = check_email(gmail_service, sender_email)
        if subject and body:
            print(f"New Email Received - Subject: {subject}")
            process_email(subject, body, youtube_service)
        time.sleep(10)  # Check every 10 seconds

if __name__ == '__main__':
    main()