import os
import time
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
    from token_manager import get_youtube_service
    try:
        # Use the token manager to get an authenticated service
        return get_youtube_service()
    except Exception as e:
        print(f"Error authenticating YouTube: {e}")
        # Fallback to legacy authentication if the token manager fails
        creds = None
        if os.path.exists("youtube_token.json"):
            creds = Credentials.from_authorized_user_file("youtube_token.json", SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            with open("youtube_token.json", "w") as token:
                token.write(creds.to_json())
        
        return build("youtube", "v3", credentials=creds)

import re

EMOJI_MAP = {
    "dead": "💀",
    "rose": "🥀",
    "flower": "🥀",
    "laugh": "😂",
    "prayer": "🙏",
    "smh": "🤦",
    "huff": "😤",
    "tuff": "😤",
    "eagle": "🦅",
    "phew": "😮‍💨",
    "cool": "😎",
    "basketball": "🏀",
    "football": "🏈",
    "xd": "😆",
    "tired": "🫩",
    "shocked": "😲",
    "smirk": "😏",
    "cry": "😭",
    "fire": "🔥",
    "cute": "🥹",
    "100": "💯",
    "eyes": "👀",
    "sweat": "😅",
    "clown": "🤡",
    "pepper": "🌶️",
    "hot": "🥵️",
    "shock": "😳",
    "angry": "😡",
    "mad": "😡",
    "heart": "❤️",
    "brokenheart": "💔",
    "check": "✅",
    "x": "❌",
    "rocket": "🚀",
}

# matches ( ... ) blocks
TOKEN_BLOCK_RE = re.compile(r"\(([^)]+)\)")

# split inside a block on spaces/commas/+ or |
SPLIT_RE = re.compile(r"[,\s+|]+")


def expand_emoji_tokens(text: str) -> str:
    """
    Replaces tokens like:
      '(skull)' -> '💀'
      '(skull fire)' -> '💀🔥'
      '(skull, fire + 100)' -> '💀🔥💯'
    Unknown tokens keep the original '(...)' block unchanged.
    Case-insensitive.
    """
    def repl(match: re.Match) -> str:
        raw = match.group(1).strip()
        parts = [p.strip().lower() for p in SPLIT_RE.split(raw) if p.strip()]
        if not parts:
            return match.group(0)

        emojis = []
        for p in parts:
            if p in EMOJI_MAP:
                emojis.append(EMOJI_MAP[p])
            else:
                # unknown token in this block -> don't replace at all (so you notice typos)
                return match.group(0)

        return "".join(emojis)

    return TOKEN_BLOCK_RE.sub(repl, text)

def generate_description(video_title: str) -> str:
    """
    Midnight Locker Room description generator:
    - Gen-Z, late-night locker-room vibe
    - punchy, scroll-optimized
    - assumes viewer gets it (no explaining)
    - boosts retention + shares
    - ends with 5–10 lowercase hashtags (no underscores)
    """
    prompt = f"""
You are the copywriter for a YouTube Shorts channel called **Midnight Locker Room**.

CHANNEL DNA (do not restate this in the output):
- Gen-Z, late-night culture hub: sports energy + internet chaos + viral moments
- Feels like a locker-room group chat after midnight (1–3 AM)
- Audience: college-aged men (18–23)
- Content types: NBA/basketball edits (LeBron-style), crashouts, fails/pranks, chaotic POV, meme culture/trending audios, ironic humor, edgy motivation, pop culture (athletes/rappers/polarizing figures)
- Tone: casual, confident, slightly unhinged. Never corporate. Never explanatory.

WRITING RULES:
- Do NOT summarize the clip. Prioritize vibe > facts.
- Assume the viewer already gets it. Avoid explaining the joke.
- Keep it short, punchy, scroll-optimized.
- Use Gen-Z rhythm/slang lightly (don’t overdo it).
- Add a quick call-to-action that fits the vibe (comment/share/tag a friend).
- Include 1–2 short lines max before hashtags (overall keep concise).
- End with 5–10 lowercase hashtags with NO underscores. Mix broad + niche (sports/memes/lockerroom vibe).

OUTPUT FORMAT (exact):
Line 1: hook (max 90 characters)
Line 2: punchy follow-up / CTA (max 120 characters)
Line 3: hashtags only

VIDEO TITLE:
{video_title}
""".strip()

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You write viral, high-retention YouTube Shorts descriptions in a specific channel voice. Follow the format exactly."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.85,
    )

    text = response.choices[0].message.content.strip()

    # Optional cleanup: ensure hashtags are on last line and are lowercase/no underscores
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if len(lines) < 3:
        return text  # keep as-is if model didn’t comply fully

    # Force last line hashtags cleanup
    hashtags = lines[-1].replace("_", "").lower()
    lines[-1] = hashtags
    return "\n".join(lines[:2] + [lines[-1]])



def add_to_playlist(youtube, playlist_name, video_id):
    """Add a video to a specific playlist."""
    # Get the playlist ID for the given playlist name
    playlists_response = youtube.playlists().list(
        part="snippet",
        mine=True,
        maxResults=50
    ).execute()

    playlist_id = None
    for playlist in playlists_response["items"]:
        if playlist["snippet"]["title"] == playlist_name:
            playlist_id = playlist["id"]
            break

    if not playlist_id:
        # Create the playlist if it doesn't exist
        playlist_request = {
            "snippet": {
                "title": playlist_name,
                "description": f"Auto-generated playlist for {playlist_name} videos"
            },
            "status": {
                "privacyStatus": "public"
            }
        }
        playlist_response = youtube.playlists().insert(
            part="snippet,status",
            body=playlist_request
        ).execute()
        playlist_id = playlist_response["id"]
        print(f"Created new playlist: {playlist_name}")

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
        scheduled_time = scheduled_time.isoformat().replace("+00:00", "Z")
    
    print(f"Debug: Attempting to schedule video at {scheduled_time}")  # Debugging scheduled time

    # Verify the file exists before attempting upload
    if not os.path.exists(file_path):
        print(f"Error: File does not exist: {file_path}")
        return None
        
    # Check if it's a valid video file by extension
    valid_video_extensions = ['.mp4', '.mov', '.avi', '.wmv', '.flv', '.mkv']
    if not any(file_path.lower().endswith(ext) for ext in valid_video_extensions):
        print(f"Warning: File may not be a video file: {file_path}")
    
    request_body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": "24"  # Entertainment category
        },
        "status": {
            "privacyStatus": "private",  # For testing purposes
            "publishAt": scheduled_time,  # ISO 8601 format
            "selfDeclaredMadeForKids": False,
            "notifySubscribers": False  # Uncheck "Publish to subscriptions feed and notify subscribers"
        }
    }

    upload_successful = False
    response = None
    
    media_file = None
    try:
        print(f"Starting upload of file: {file_path}")
        media_file = MediaFileUpload(file_path, chunksize=-1, resumable=True)
        
        response = youtube.videos().insert(
            part="snippet,status",
            body=request_body,
            media_body=media_file
        ).execute()

        print(f"Video uploaded successfully. Video ID: {response['id']}")
        upload_successful = True

        # Add the video to the specified playlist
        add_to_playlist(youtube, playlist_name, response["id"])
        
    except Exception as e:
        print(f"Error uploading video: {e}")
        return None
    
    finally:
        # Make sure to close the media file if it was opened
        if media_file:
            try:
                if hasattr(media_file, 'close'):
                    media_file.close()
                # For MediaFileUpload, we may need to set it to None to release file handle
                media_file = None
            except Exception as e:
                print(f"Error closing media file: {e}")
        
        # Only delete if upload was successful
        if upload_successful:
            # Add a short delay to ensure file handles are fully released
            import time
            time.sleep(7)
            
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"Successfully deleted video file: {file_path}")
                else:
                    print(f"Warning: Video file not found for deletion: {file_path}")
            except Exception as e:
                print(f"Error deleting video file {file_path}: {e}")
                print("Will try to delete again in 3 seconds...")
                
                # Try one more time after a delay
                time.sleep(3)
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        print(f"Successfully deleted video file on second attempt: {file_path}")
                except Exception as e2:
                    print(f"Error on second delete attempt: {e2}")
    
    return response


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
    Calculate the next upload time based on preferred schedule throughout the day.
    Uses last_upload_time.txt as the source of truth.
    """
    # Define preferred upload times in local time (every 3 hours throughout the day)
    preferred_hours = [0, 3, 6, 9, 12, 15, 18, 21]  # 12am, 3am, 6am, 9am, 12pm, 3pm, 6pm, 9pm
    #preferred_hours = [9, 12, 15, 18, 21]  #9am, 12pm, 3pm, 6pm, 9pm
    #preferred_hours = [9, 13, 17, 21]  #9am, 1pm, 5pm, 9pm
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
        
        # First, find which hour slot the last upload was in
        last_hour = last_upload_time.hour
        
        # Find the next hour in our schedule
        next_hour = None
        next_day = False
        
        # Check if the last hour is in our schedule
        if last_hour in preferred_hours:
            # Find the next hour in the sequence
            index = preferred_hours.index(last_hour)
            if index < len(preferred_hours) - 1:
                # There's another slot today
                next_hour = preferred_hours[index + 1]
            else:
                # Move to the first slot tomorrow
                next_hour = preferred_hours[0]
                next_day = True
        else:
            # Find the next available hour
            for hour in preferred_hours:
                if hour > last_hour:
                    next_hour = hour
                    break
            
            # If no slot found today, use the first slot tomorrow
            if next_hour is None:
                next_hour = preferred_hours[0]
                next_day = True
        
        # Create the datetime for the next slot
        if next_day:
            next_date = last_upload_time.date() + timedelta(days=1)
        else:
            next_date = last_upload_time.date()
        
        next_slot = datetime(
            next_date.year,
            next_date.month,
            next_date.day,
            next_hour, 0, tzinfo=local_tz
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
                preferred_hours[0], 0, tzinfo=local_tz
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
                preferred_hours[0], 0, tzinfo=local_tz
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
        print(f"Comment pinned successfully for video {video_id}")

    except Exception as e:
        print(f"Error processing comments for video {video_id}: {e}")


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