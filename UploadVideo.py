import os
import time
import base64
import subprocess
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

from instagram_downloader import download_instagram_reel
from YoutubeUpload import (
    upload_video,
    authenticate_youtube,
    generate_description,
    read_last_upload_time,
    write_last_upload_time,
    calculate_next_upload_time,
    expand_emoji_tokens
)

load_dotenv()

# Keep your same behavior defaults
TITLE_VIRAL = True

# Gmail scope (same as your file)
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


def authenticate_gmail():
    """Authenticate with Gmail API and return the service object."""
    try:
        from token_manager import get_gmail_service
        return get_gmail_service(full_access=False)
    except Exception as e:
        print(f"Error authenticating Gmail: {e}")
        creds = None
        if os.path.exists("token.json"):
            from google.oauth2.credentials import Credentials
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
                creds = flow.run_local_server(port=0)
            with open("token.json", "w") as token:
                token.write(creds.to_json())

        return build("gmail", "v1", credentials=creds)


def trash_email(service, msg_id: str):
    """Move one specific email to Trash (recoverable)."""
    service.users().messages().trash(userId="me", id=msg_id).execute()
    print(f"🗑️ Trashed email: {msg_id}")

def safe_delete_file(path: str):
    try:
        if path and os.path.exists(path):
            os.remove(path)
            print(f"🧹 Deleted local video: {path}")
    except Exception as e:
        print(f"⚠️ Could not delete file {path}: {e}")

def check_email(service, sender_email):
    """Check for new unread emails from a specific sender."""
    results = service.users().messages().list(
        userId="me",
        q=f"from:{sender_email} is:unread"
    ).execute()

    messages = results.get("messages", [])
    if not messages:
        print("No new emails.")
        return None, None, None  # CHANGED

    msg_id = messages[0]["id"]
    message = service.users().messages().get(userId="me", id=msg_id).execute()
    payload = message["payload"]
    headers = payload.get("headers", [])

    # Extract subject
    subject = ""
    for header in headers:
        if header.get("name") == "Subject":
            subject = header.get("value", "")

    if TITLE_VIRAL or not subject:
        subject = "Viral"

    # Extract body (try plain; fallback parse HTML for IG link)
    body = ""
    if "data" in payload.get("body", {}):
        body = base64.urlsafe_b64decode(payload["body"]["data"]).decode(errors="ignore")
    elif "parts" in payload:
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain" and "data" in part.get("body", {}):
                body = base64.urlsafe_b64decode(part["body"]["data"]).decode(errors="ignore")
            elif part.get("mimeType") == "text/html" and "data" in part.get("body", {}):
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(
                    base64.urlsafe_b64decode(part["body"]["data"]).decode(errors="ignore"),
                    "html.parser",
                )
                links = soup.find_all("a")
                for link in links:
                    href = link.get("href", "")
                    if "instagram.com" in href:
                        body = href
                        break

    # Mark as read
    service.users().messages().modify(
        userId="me",
        id=msg_id,
        body={"removeLabelIds": ["UNREAD"]}
    ).execute()

    return msg_id, subject, body  # CHANGED


def play_video_then_wait(video_path: str):
    """
    Opens the video using Windows default player.
    We can't reliably detect "close" for every player, so we ask you to press ENTER
    after you close it. This preserves your exact flow without heavy dependencies.
    """
    print("\n▶ Opening video. Close the player when you're done watching.")
    # This opens default app; returns immediately.
    subprocess.run(["cmd", "/c", "start", "", video_path], shell=True)
    input("Press ENTER after you close the video window...")


def process_email(gmail_service, msg_id, subject, body, youtube):  # CHANGED
    """Extract Instagram URL, download the video, play it, then prompt for title and upload."""
    if not (body and body.startswith("https://www.instagram.com")):
        print("No valid Instagram URL found in the email body.")
        return

    print(f"Downloading video from: {body}")

    downloads_folder = r"C:\Users\super\Downloads"

    # Download with subject as filename (same as your logic)
    downloaded_path = download_instagram_reel(body, downloads_folder, subject)

    if not downloaded_path:
        print("Failed to download Instagram video.")
        return

    print(f"Downloaded video saved as: {downloaded_path}")

    # play video first
    play_video_then_wait(downloaded_path)

    # after exit, ask for name/title
    typed_title_raw = input("\nName the content (or type 'delete' to skip): ").strip()

    # If user wants to skip this clip entirely:
    if typed_title_raw.lower() == "delete":
        print("🗑️ Skipping: deleting video + trashing email...")
        safe_delete_file(downloaded_path)
        trash_email(gmail_service, msg_id)
        return  # move on to next email

    typed_title = expand_emoji_tokens(typed_title_raw)
    print(f"Title preview: {typed_title}")

    if not typed_title:
        print("❌ Title cannot be empty. Defaulting title to subscribe")
        typed_title = "subscribe #midnightlockerroom"


    description = generate_description(typed_title) + "\n\nsubscribe! Midnightlockerroom"

    tags = ["midnightlockerroom", "shorts", "culture", "college", "humor"]
    playlist_name = "college culture compilation 2026"

    # Read last upload time from file
    last_upload_time = read_last_upload_time()

    # Schedule next upload time using ONLY the file data
    next_upload_time = calculate_next_upload_time(youtube, last_upload_time, check_youtube_api=False)

    # Ensure at least 15 minutes in the future
    local_tz = datetime.now().astimezone().tzinfo
    now_local = datetime.now(local_tz)
    now_utc = now_local.astimezone(timezone.utc)

    if next_upload_time <= now_utc + timedelta(minutes=15):
        print(f"Warning: Calculated upload time {next_upload_time} is too soon. Adjusting...")
        fallback_time = now_local + timedelta(minutes=20)
        next_upload_time = fallback_time.astimezone(timezone.utc)
        print(f"Using fallback time: {fallback_time}")

    # Upload video to YouTube using the typed title
    response = upload_video(  # CHANGED (capture response)
        youtube,
        downloaded_path,
        typed_title,
        description,
        tags,
        next_upload_time,
        playlist_name
    )

    if not response:
        print("❌ Upload failed. Not deleting email.")
        return

    # Update the last upload time (store in local time for readability)
    next_local_time = next_upload_time.astimezone(local_tz)
    write_last_upload_time(next_local_time)

    # ✅ Delete email only after upload succeeded AND the file is gone
    if not os.path.exists(downloaded_path):
        trash_email(gmail_service, msg_id)
    else:
        print("⚠️ Upload succeeded but file still exists, so email was NOT deleted.")

    print("Video uploaded successfully!")


def main():
    sender_email = os.getenv("SENDER_EMAIL")
    if not sender_email:
        print("❌ Missing SENDER_EMAIL in your .env")
        return

    gmail_service = authenticate_gmail()
    youtube_service = authenticate_youtube()

    last_upload_time = read_last_upload_time()
    if last_upload_time:
        print(f"Initial last upload time from file: {last_upload_time}")
    else:
        print("No previous upload time found in file.")

    print("Monitoring for emails...")

    while True:
        msg_id, subject, body = check_email(gmail_service, sender_email)  # CHANGED
        if msg_id and subject and body:
            print(f"New Email Received - Subject: {subject}")
            process_email(gmail_service, msg_id, subject, body, youtube_service)  # CHANGED
        time.sleep(10)


if __name__ == "__main__":
    main()
