import os
from datetime import datetime, timedelta, timezone
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Constants
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube"
]
LAST_UPLOAD_FILE = "last_upload_time.txt"  # File to store the last upload time


def authenticate_youtube():
    """Authenticate with YouTube API and return the service object."""
    creds = None
    if os.path.exists("youtube_token.json"):
        creds = Credentials.from_authorized_user_file("youtube_token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("youtube_token.json", "w") as token:
            token.write(creds.to_json())
    return build("youtube", "v3", credentials=creds)


def generate_description(video_title):
    """Generate a YouTube video description using OpenAI."""
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {
                "role": "user",
                "content": f"Write a compelling YouTube Shorts description for a video titled: '{video_title}'. Include hashtags and make it engaging. It's a comedy video and it's funny."
            }
        ],
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()


def add_to_playlist(youtube, playlist_name, video_id):
    """Add a video to a specific playlist."""
    # Get the playlist ID for the given playlist name
    playlists_response = youtube.playlists().list(
        part="snippet",
        mine=True,  # Get playlists belonging to the authenticated user
        maxResults=50
    ).execute()

    playlist_id = None
    for playlist in playlists_response["items"]:
        if playlist["snippet"]["title"].lower() == playlist_name.lower():
            playlist_id = playlist["id"]
            break

    if not playlist_id:
        print(f"Error: Playlist '{playlist_name}' not found.")
        return

    # Add the video to the playlist
    request_body = {
        "snippet": {
            "playlistId": playlist_id,
            "resourceId": {
                "kind": "youtube#video",
                "videoId": video_id
            }
        }
    }

    youtube.playlistItems().insert(
        part="snippet",
        body=request_body
    ).execute()

    print(f"Video added to playlist: {playlist_name}")


def upload_video(youtube, file_path, title, description, tags, scheduled_time, playlist_name):
    """Upload video to YouTube and add it to a playlist."""
    print(f"Debug: Attempting to schedule video at {scheduled_time}")  # Debugging scheduled time

    request_body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": "23"  # Category: Comedy
        },
        "status": {
            "privacyStatus": "private",  # For testing purposes
            "publishAt": scheduled_time,  # ISO 8601 format
            "selfDeclaredMadeForKids": False,
            "notifySubscribers": False  # Uncheck "Publish to subscriptions feed and notify subscribers"
        }
    }

    media_file = MediaFileUpload(file_path, chunksize=-1, resumable=True)
    response = youtube.videos().insert(
        part="snippet,status",
        body=request_body,
        media_body=media_file
    ).execute()

    print(f"Video uploaded successfully. Video ID: {response['id']}")

    # Add the video to the specified playlist
    add_to_playlist(youtube, playlist_name, response["id"])


def read_last_upload_time():
    """Read the last upload time from the file."""
    if os.path.exists(LAST_UPLOAD_FILE):
        with open(LAST_UPLOAD_FILE, "r") as file:
            timestamp = file.read().strip()
            if timestamp:
                return datetime.fromisoformat(timestamp)
    return None


def write_last_upload_time(upload_time):
    """Write the last upload time to the file."""
    with open(LAST_UPLOAD_FILE, "w") as file:
        file.write(upload_time.isoformat())


def calculate_next_upload_time(last_upload_time):
    """Calculate the next upload time in 75-minute increments."""
    now = datetime.now(timezone.utc)

    # Hardcode the first upload to 6:00 AM UTC on 12/30/2024
    first_upload_time = datetime(2024, 12, 30, 6, 0, tzinfo=timezone.utc)
    if not last_upload_time:
        # Ensure the first upload time is valid
        if first_upload_time > now + timedelta(minutes=15):
            return first_upload_time
        else:
            return now + timedelta(minutes=75)

    # Increment the last upload time by 75 minutes
    next_time = last_upload_time + timedelta(minutes=75)

    # Ensure the next upload time is at least 15 minutes in the future
    while next_time <= now + timedelta(minutes=15):
        next_time += timedelta(minutes=75)

    # Return properly formatted and aligned time
    return next_time.replace(second=0, microsecond=0)


def main():
    youtube = authenticate_youtube()
    video_file = r"C:\Users\super\Downloads\watch him.mp4"  # Ensure this path is correct
    video_title = "watch him⏰🤣"

    # Check if the file exists
    if not os.path.exists(video_file):
        print(f"Error: File '{video_file}' not found. Please check the path and try again.")
        return

    # Generate description
    description = generate_description(video_title)
    print(f"Generated Description:\n{description}")

    # Add tags
    tags = ["Shorts", "Viral", "fyp", "memes", "Funny", "Trending", "Entertainment", "FYP", "dailymemes", "Comedy",
            "humor", "relatable", "hilarious", "LOL", "Jokes", "LaughOutLoud", "FunnyVideo", "skit", "funnyshorts",
            "ComedyShorts", "ViralComedy", "funnycontent", "dailycomedy", "funnyvideo"]

    # Read the last upload time from the file
    last_upload_time = read_last_upload_time()
    next_upload_time = calculate_next_upload_time(last_upload_time)

    # Format the next upload time for YouTube
    next_upload_time_iso = next_upload_time.isoformat().replace("+00:00", "Z")
    print(f"Scheduling video for: {next_upload_time_iso}")

    # Playlist name
    playlist_name = "memes"

    # Upload video and add it to the playlist
    upload_video(youtube, video_file, video_title, description, tags, next_upload_time_iso, playlist_name)

    # Update the last upload time in the file
    write_last_upload_time(next_upload_time)
    print("Upload complete!")


if __name__ == "__main__":
    main()