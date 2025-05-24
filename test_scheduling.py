from YoutubeUpload import read_last_upload_time, calculate_next_upload_time, authenticate_youtube
from datetime import datetime, timedelta, timezone

def test_scheduling():
    """Test that the scheduling algorithm works correctly by simulating several uploads."""
    # Authenticate YouTube (needed for the function)
    youtube = authenticate_youtube()

    # Read current last upload time
    last_upload = read_last_upload_time()
    print(f"Starting test with last upload time: {last_upload}")

    # Simulate multiple uploads to verify the pattern
    for i in range(10):
        # Get next upload time
        next_upload = calculate_next_upload_time(youtube, last_upload, check_youtube_api=False)
        
        # Convert to local time for easier reading
        local_tz = datetime.now().astimezone().tzinfo
        next_upload_local = next_upload.astimezone(local_tz)
        
        # Print the scheduled time
        print(f"Upload {i+1}: {next_upload_local.strftime('%Y-%m-%d %H:%M')} - Hour: {next_upload_local.hour}")
        
        # Set this as the last upload for the next iteration
        last_upload = next_upload_local

if __name__ == "__main__":
    test_scheduling()
