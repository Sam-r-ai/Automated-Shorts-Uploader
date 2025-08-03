import os
import sys
import shutil
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

def test_file_deletion():
    """Test if upload_video function deletes files after upload"""
    # Create a temporary test file with .mp4 extension to simulate a real video
    test_dir = os.path.dirname(os.path.abspath(__file__))
    test_file_path = os.path.join(test_dir, "test_video_for_deletion.mp4")
    
    # Create dummy file
    with open(test_file_path, "w") as f:
        f.write("This is a test file simulating a video.")
    
    print(f"Created test file: {test_file_path}")
    print(f"File exists before upload: {os.path.exists(test_file_path)}")
    
    # Save original function
    import YoutubeUpload
    original_add_to_playlist = YoutubeUpload.add_to_playlist
    
    try:
        # Override the add_to_playlist function with our mock
        YoutubeUpload.add_to_playlist = mock_add_to_playlist
        
        # Create mock YouTube service
        youtube = MockYouTubeService()
        
        # Set up parameters for upload
        title = "Test Video - Delete After Upload"
        description = "This is a test video to verify file deletion functionality."
        tags = ["test", "delete"]
        scheduled_time = datetime.now(timezone.utc) + timedelta(minutes=30)
        playlist_name = "test_playlist"
        
        # Call upload function with our mock
        print("\nAttempting mock upload...")
        result = upload_video(youtube, test_file_path, title, description, tags, scheduled_time, playlist_name)
        print("Upload result:", result)
        
        # Check if file was deleted after successful mock upload
        print(f"\nFile exists after upload attempt: {os.path.exists(test_file_path)}")
        
    finally:
        # Restore original function
        YoutubeUpload.add_to_playlist = original_add_to_playlist
        
        # Clean up if file still exists
        if os.path.exists(test_file_path):
            print("Cleaning up test file...")
            os.remove(test_file_path)

if __name__ == "__main__":
    print("===== Testing File Deletion After Upload =====")
    test_file_deletion()
    print("===== Test Complete =====")
