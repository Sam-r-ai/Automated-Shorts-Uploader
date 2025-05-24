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
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": f"Write a compelling and engaging YouTube Shorts description that is SEO optimized with many keywords for a video titled: '{video_title}'. Include hashtags that are all underscore and make it engaging. Do not use underscores. It's a comedy video and it's funny."
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
    # Make sure the scheduled_time is in UTC and properly formatted for YouTube API
    if isinstance(scheduled_time, datetime):
        if scheduled_time.tzinfo != timezone.utc:
            scheduled_time = scheduled_time.astimezone(timezone.utc)
        scheduled_time = scheduled_time.isoformat().replace("+00:00", "Z")
    
    print(f"Debug: Attempting to schedule video at {scheduled_time}")  # Debugging scheduled time

    request_body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": "24"  # Category: Comedy
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


def calculate_next_upload_time(youtube, last_upload_time=None, check_youtube_api=False):
    """
    Calculate the next upload time based on preferred schedule of 9 AM, 1 PM, and 8 PM local time.
    Uses last_upload_time.txt as the source of truth.
    """
    # Define preferred upload times in local time (9 AM, 1 PM, and 8 PM)
    preferred_hours = [9, 13, 20]
    
    # Get current time in local timezone
    local_tz = datetime.now().astimezone().tzinfo
    now = datetime.now(local_tz)
    
    # Process the last upload time from the file
    if last_upload_time:
        # Convert string timestamp to datetime if needed
        if isinstance(last_upload_time, str):
            try:
                last_upload_time = datetime.fromisoformat(last_upload_time)
                # Ensure it has timezone info
                if last_upload_time.tzinfo is None:
                    last_upload_time = last_upload_time.replace(tzinfo=timezone.utc).astimezone(local_tz)
                else:
                    last_upload_time = last_upload_time.astimezone(local_tz)
            except ValueError:
                print(f"Warning: Could not parse last upload time '{last_upload_time}'")
                last_upload_time = None
        elif last_upload_time.tzinfo:
            # Convert existing datetime to local time zone
            last_upload_time = last_upload_time.astimezone(local_tz)
            print(f"Converted last upload time to: {last_upload_time}")
    
    # Start generating slots from today
    current_date = now.date()
    
    # If we have a last upload time, start from its date
    if last_upload_time:
        print(f"Last upload time: {last_upload_time}")
        # Find the next slot after the last upload
        
        # Case 1: Last upload was at 9 AM, next should be 1 PM same day
        if last_upload_time.hour == 9:
            next_slot = datetime(
                last_upload_time.year, 
                last_upload_time.month, 
                last_upload_time.day, 
                13, 0, tzinfo=local_tz
            )
        
        # Case 2: Last upload was at 1 PM, next should be 8 PM same day
        elif last_upload_time.hour == 13:
            next_slot = datetime(
                last_upload_time.year, 
                last_upload_time.month, 
                last_upload_time.day, 
                20, 0, tzinfo=local_tz
            )
        
        # Case 3: Last upload was at 8 PM, next should be 9 AM next day
        elif last_upload_time.hour == 20:
            next_day = last_upload_time.date() + timedelta(days=1)
            next_slot = datetime(
                next_day.year, 
                next_day.month, 
                next_day.day, 
                9, 0, tzinfo=local_tz
            )
        
        # Case 4: Last upload was at some other time, find the next available slot
        else:
            # Start checking from last upload date
            check_date = last_upload_time.date()
            
            # Try to find a slot on the same day
            found = False
            for hour in preferred_hours:
                potential_slot = datetime(
                    check_date.year, 
                    check_date.month, 
                    check_date.day, 
                    hour, 0, tzinfo=local_tz
                )
                if potential_slot > last_upload_time:
                    next_slot = potential_slot
                    found = True
                    break
            
            # If no slot found on same day, move to next day's first slot
            if not found:
                next_day = check_date + timedelta(days=1)
                next_slot = datetime(
                    next_day.year, 
                    next_day.month, 
                    next_day.day, 
                    9, 0, tzinfo=local_tz
                )
    else:
        # No last upload time, find the next available slot from now
        found = False
        
        # Try today's slots
        for hour in preferred_hours:
            potential_slot = datetime(
                current_date.year, 
                current_date.month, 
                current_date.day, 
                hour, 0, tzinfo=local_tz
            )
            # Need at least 15 minutes in the future
            if potential_slot > now + timedelta(minutes=15):
                next_slot = potential_slot
                found = True
                break
        
        # If no suitable slot today, use tomorrow's first slot
        if not found:
            next_day = current_date + timedelta(days=1)
            next_slot = datetime(
                next_day.year, 
                next_day.month, 
                next_day.day, 
                9, 0, tzinfo=local_tz
            )
    
    # Final safety check: ensure the slot is at least 15 minutes in the future
    min_future_time = now + timedelta(minutes=15)
    if next_slot < min_future_time:
        print(f"Warning: Calculated time {next_slot} is less than 15 minutes in the future!")
        
        # Find the next available slot from the current time
        found = False
        check_date = now.date()
        
        # Try today's remaining slots
        for hour in preferred_hours:
            potential_slot = datetime(
                check_date.year, 
                check_date.month, 
                check_date.day, 
                hour, 0, tzinfo=local_tz
            )
            if potential_slot >= min_future_time:
                next_slot = potential_slot
                found = True
                break
                
        # If no suitable slot today, use tomorrow's first slot
        if not found:
            next_day = check_date + timedelta(days=1)
            next_slot = datetime(
                next_day.year, 
                next_day.month, 
                next_day.day, 
                9, 0, tzinfo=local_tz
            )
    
    # YouTube API requires UTC time in ISO format
    next_slot_utc = next_slot.astimezone(timezone.utc)
    
    print(f"Scheduled next upload for: {next_slot.strftime('%Y-%m-%d %H:%M:%S')} {local_tz}")
    print(f"  (which is {next_slot_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC)")
    
    return next_slot_utc

def update_all_video_categories_to_entertainment(youtube):
    """Update the category of all uploaded videos to 'Entertainment'."""
    # Use the search.list() method to retrieve uploaded videos
    request = youtube.search().list(
        part="id",
        forMine=True,
        type="video",
        maxResults=500  # Fetch up to 50 videos per request
    )

    response = request.execute()

    for item in response.get("items", []):
        video_id = item["id"]["videoId"]

        # Retrieve the full snippet for the video
        video_request = youtube.videos().list(
            part="snippet",
            id=video_id
        )
        video_response = video_request.execute()

        if video_response["items"]:
            video = video_response["items"][0]
            snippet = video["snippet"]
            current_category = snippet.get("categoryId")

            if current_category != "24":
                print(f"Updating video '{snippet['title']}' (ID: {video_id}) to category 'Entertainment'.")
                
                snippet["categoryId"] = "24"  # Set to Entertainment

                youtube.videos().update(
                    part="snippet",
                    body={
                        "id": video_id,
                        "snippet": snippet
                    }
                ).execute()

                print(f"Video '{snippet['title']}' updated successfully.")
            else:
                print(f"Video '{snippet['title']}' is already in the 'Entertainment' category.")

    print("All videos processed.")

def get_all_uploaded_videos(youtube):
    """Retrieve all uploaded videos for the authenticated user's channel."""
    videos = []
    request = youtube.search().list(
        part="id",
        forMine=True,
        type="video",
        maxResults=50
    )
    while request:
        response = request.execute()
        for item in response.get("items", []):
            video_id = item["id"]["videoId"]
            videos.append(video_id)
        request = youtube.search().list_next(request, response)
    return videos


def comment_and_pin_on_video(youtube, video_id, comment_text="Like and subscribe for more!"):
    """Comment on a video and pin the comment only if there isn't already a pinned comment."""
    try:
        # Step 1: Check if there's already a pinned comment
        comment_threads_response = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=100  # Fetch up to 100 comments
        ).execute()

        for comment_thread in comment_threads_response.get("items", []):
            # Check if the comment is pinned
            comment_snippet = comment_thread["snippet"]["topLevelComment"]["snippet"]
            if comment_snippet.get("isPinned", False):
                print(f"A pinned comment already exists for video {video_id}: {comment_snippet['textDisplay']}")
                return

        # Step 2: No pinned comment exists; post and pin a new comment
        print(f"No pinned comment found for video {video_id}. Posting a new comment...")
        comment_request_body = {
            "snippet": {
                "videoId": video_id,
                "topLevelComment": {
                    "snippet": {
                        "textOriginal": comment_text
                    }
                }
            }
        }

        comment_response = youtube.commentThreads().insert(
            part="snippet",
            body=comment_request_body
        ).execute()

        comment_id = comment_response["id"]
        print(f"Comment posted successfully for video {video_id}. Comment ID: {comment_id}")

        # Step 3: Pin the new comment
        youtube.comments().setModerationStatus(
            id=comment_id,
            moderationStatus="published",
            banAuthor=False
        ).execute()

        print(f"Comment pinned successfully for video {video_id}!")
    except Exception as e:
        print(f"An error occurred while processing video {video_id}: {e}")


def process_all_videos_and_comment(youtube, comment_text="Like and subscribe for more!"):
    """Retrieve all videos and add a pinned comment if none exists."""
    videos = get_all_uploaded_videos(youtube)
    print(f"Retrieved {len(videos)} videos from the channel.")
    for video_id in videos:
        comment_and_pin_on_video(youtube, video_id, comment_text)
    print("Processed all videos.")

def main():
    youtube = authenticate_youtube()
    #update_all_video_categories_to_entertainment(youtube)
    #process_all_videos_and_comment(youtube, comment_text="Like and subscribe for more!")
    #video_file = r"C:\Users\super\Downloads\Messi or Ronaldo #memes #soccer #football #clubmarsmemes.mp4" # Ensure this path is correct
    #video_title = "Messi or Ronaldo? #memes #soccer #football #clubmarsmemes.mp4"

    # Check if the file exists
    #if not os.path.exists(video_file):
    #    print(f"Error: File '{video_file}' not found. Please check the path and try again.")
    #    return

    # Generate description
    #description = generate_description(video_title)
    #print(f"Generated Description:\n{description}")

    # Add tags
    #tags = ["shorts", "viral", "fyp", "memes", "funny", "trending", "entertainment", "dailymemes", "comedy",
     #       "humor", "relatable", "hilarious", "lol", "jokes", "laughoutloud", "skit", "funnyshorts",
    #        "comedyshorts", "viralcomedy", "funnycontent", "dailycomedy", "funnyvideo"]

    # Read the last upload time from the file
   # last_upload_time = read_last_upload_time()
    #next_upload_time = calculate_next_upload_time(last_upload_time)

    # Format the next upload time for YouTube
    #next_upload_time_iso = next_upload_time.isoformat().replace("+00:00", "Z")
   # print(f"Scheduling video for: {next_upload_time_iso}")

    # Playlist name
    #playlist_name = "memes"

    # Upload video and add it to the playlist
    #upload_video(youtube, video_file, video_title, description, tags, next_upload_time_iso, playlist_name)

    # Update the last upload time in the file
   # write_last_upload_time(next_upload_time)
    #print("Upload complete!")


if __name__ == "__main__":
    main()