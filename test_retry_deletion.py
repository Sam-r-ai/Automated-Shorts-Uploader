import os
import sys
import time
import random
import string
import threading
from datetime import datetime, timedelta, timezone
from YoutubeUpload import upload_video

# Mock YouTube API for testing
class MockYouTubeService:
    def videos(self):
        return self
        
    def insert(self, part, body, media_body):
        return self
        
    def execute(self):
        return {"id": "mock_video_id_12345"}

# Mock playlist function
def mock_add_to_playlist(youtube, playlist_name, video_id):
    print(f"[MOCK] Added video {video_id} to playlist {playlist_name}")
    return True

def create_dummy_video(file_path, size_kb=500):
    """Create a dummy video file with random content"""
    # Generate random data
    random_data = ''.join(random.choices(string.ascii_letters + string.digits, k=size_kb * 1024))
    
    # Write to file
    with open(file_path, "w") as f:
        f.write(random_data)
    
    return file_path

def file_access_thread(file_path, duration=2):
    """Thread that keeps a file open for reading for the specified duration"""
    print(f"Starting file access thread. Will keep file open for {duration} seconds...")
    try:
        # Open the file for reading to simulate a file lock
        with open(file_path, 'r') as f:
            # Keep the file open for the specified duration
            time.sleep(duration)
            # Read something to make sure the file handle is actually used
            f.read(10)
        print("File access thread completed")
    except Exception as e:
        print(f"Error in file access thread: {e}")

def test_deletion_with_file_in_use():
    """Test file deletion when the file is initially in use"""
    # Create a temporary video file in the Downloads folder
    downloads_folder = os.path.join(os.path.expanduser("~"), "Downloads")
    test_video_filename = f"test_video_in_use_{int(time.time())}.mp4"
    test_video_path = os.path.join(downloads_folder, test_video_filename)
    
    try:
        # Create a test video file
        print(f"Creating test video file at: {test_video_path}")
        create_dummy_video(test_video_path, size_kb=500)  # 500KB file
        
        if not os.path.exists(test_video_path):
            print("Failed to create test file!")
            return
            
        # Start a thread that will keep the file open for reading
        access_thread = threading.Thread(
            target=file_access_thread,
            args=(test_video_path, 2)  # Keep file open for 2 seconds
        )
        access_thread.start()
        
        # Save original function
        import YoutubeUpload
        original_add_to_playlist = YoutubeUpload.add_to_playlist
        
        try:
            # Override the add_to_playlist function with our mock
            YoutubeUpload.add_to_playlist = mock_add_to_playlist
            
            # Create mock YouTube service
            youtube = MockYouTubeService()
            
            # Set up parameters for upload
            title = "Test Video With File In Use"
            description = "This is a test to verify deletion retry works."
            tags = ["test"]
            scheduled_time = datetime.now(timezone.utc) + timedelta(minutes=30)
            playlist_name = "test_playlist"
            
            print(f"\nSimulating video upload with file in use...")
            
            # Call upload function with our mock while file is being held open
            result = upload_video(youtube, test_video_path, title, description, tags, scheduled_time, playlist_name)
            
            print("Upload result:", result)
            
            # Check if file was eventually deleted after retry
            time.sleep(5)  # Allow time for the retry logic
            print(f"\nChecking if file was deleted after upload and retry...")
            print(f"File exists after upload: {os.path.exists(test_video_path)}")
            
            if os.path.exists(test_video_path):
                print("❌ Test failed: File was not deleted after upload and retry!")
            else:
                print("✅ Test passed: File was successfully deleted after upload with retry!")
                
        finally:
            # Restore original function
            YoutubeUpload.add_to_playlist = original_add_to_playlist
            
    except Exception as e:
        print(f"Test error: {e}")
        
    finally:
        # Make sure we clean up if the file still exists
        if os.path.exists(test_video_path):
            print("Cleaning up test file...")
            try:
                os.remove(test_video_path)
            except Exception as e:
                print(f"Error cleaning up: {e}")

if __name__ == "__main__":
    print("===== Testing File Deletion With File In Use =====")
    test_deletion_with_file_in_use()
    print("===== Test Complete =====")
