import os
import time
import tempfile
import shutil
import random
import string
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

def test_real_workflow():
    """Test the real workflow to ensure the deletion works in practice"""
    # Create a temporary video file in the actual Downloads folder
    downloads_folder = os.path.join(os.path.expanduser("~"), "Downloads")
    test_video_filename = f"test_instagram_video_{int(time.time())}.mp4"
    test_video_path = os.path.join(downloads_folder, test_video_filename)
    
    try:
        # Create a larger dummy video file to better simulate a real video
        print(f"Creating test video file at: {test_video_path}")
        create_dummy_video(test_video_path, size_kb=1000)  # 1MB file
        
        if os.path.exists(test_video_path):
            print(f"Test file created successfully. Size: {os.path.getsize(test_video_path) / 1024:.1f} KB")
        else:
            print("Failed to create test file!")
            return
        
        # Save original function
        import YoutubeUpload
        original_add_to_playlist = YoutubeUpload.add_to_playlist
        
        try:
            # Override the add_to_playlist function with our mock
            YoutubeUpload.add_to_playlist = mock_add_to_playlist
            
            # Create mock YouTube service
            youtube = MockYouTubeService()
            
            # Set up parameters for upload
            title = "Test Instagram Video"
            description = "This is a test video to verify file deletion functionality."
            tags = ["test", "delete", "shorts"]
            scheduled_time = datetime.now(timezone.utc) + timedelta(minutes=30)
            playlist_name = "test_playlist"
            
            print(f"\nSimulating video upload workflow...")
            print(f"File exists before upload: {os.path.exists(test_video_path)}")
            
            # Call upload function with our mock - this should simulate the real workflow
            result = upload_video(youtube, test_video_path, title, description, tags, scheduled_time, playlist_name)
            
            print("Upload result:", result)
            print(f"\nChecking if file was deleted after upload...")
            print(f"File exists after upload: {os.path.exists(test_video_path)}")
            
            if os.path.exists(test_video_path):
                print("❌ Test failed: File was not deleted after upload!")
            else:
                print("✅ Test passed: File was successfully deleted after upload!")
                
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
    print("===== Testing Real Workflow Deletion =====")
    test_real_workflow()
    print("===== Test Complete =====")
