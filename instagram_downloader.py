import instaloader
import os
import re
import time
import random
import shutil

def download_instagram_reel(url, output_dir=None, custom_filename=None):
    """
    Download Instagram reel video using instaloader library
    
    Args:
        url: Instagram reel URL
        output_dir: Directory to save the video (default: user's Downloads folder)
        custom_filename: Custom filename to use (without extension)
    
    Returns:
        Path to the downloaded video file or None if download failed
    """
    # Set default output directory if not provided
    if not output_dir:
        output_dir = os.path.join(os.path.expanduser("~"), "Downloads")
    
    # Make sure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Extract post shortcode from URL
    shortcode_match = re.search(r'/(p|reel|tv)/([^/?]+)', url)
    if not shortcode_match:
        print(f"❌ Invalid Instagram URL: {url}")
        return None
    
    shortcode = shortcode_match.group(2)
    print(f"📋 Extracted shortcode: {shortcode}")
    
    # Define the final output path if custom filename is provided
    final_output_path = None
    if custom_filename:
        if not custom_filename.endswith('.mp4'):
            custom_filename += '.mp4'
        final_output_path = os.path.join(output_dir, custom_filename)
        
        # Check if file already exists with this name
        if os.path.exists(final_output_path) and os.path.getsize(final_output_path) > 0:
            print(f"✅ File already exists with requested name: {final_output_path}")
            return final_output_path
    
    # Initialize Instaloader with custom settings
    L = instaloader.Instaloader(
        download_videos=True,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        compress_json=False,
        post_metadata_txt_pattern="",
        dirname_pattern=output_dir,
        quiet=False,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    )
    
    try:
        # Add random delay to avoid rate limiting
        delay = random.uniform(2, 5)
        print(f"⏳ Adding delay of {delay:.1f}s to avoid rate limiting...")
        time.sleep(delay)
        
        # Download the post by shortcode
        print(f"⏱️ Downloading reel {shortcode}...")
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        
        # Create a temporary directory for initial download
        temp_dir = os.path.join(output_dir, f"temp_{shortcode}_{int(time.time())}")
        os.makedirs(temp_dir, exist_ok=True)
        
        # Download the post to temporary directory
        L.dirname_pattern = temp_dir
        L.download_post(post, target=shortcode)
        
        # Find the downloaded video file in temporary directory
        temp_video_path = None
        for file in os.listdir(temp_dir):
            if file.endswith(".mp4"):
                temp_video_path = os.path.join(temp_dir, file)
                break
        
        if not temp_video_path:
            print("⚠️ No video file found in download directory")
            # Clean up temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)
            return None
        
        # Move file to final destination with desired name
        if final_output_path:
            if os.path.exists(final_output_path):
                os.remove(final_output_path)
            shutil.move(temp_video_path, final_output_path)
            print(f"✅ Video saved directly as: {final_output_path}")
            # Clean up temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)
            return final_output_path
        else:
            # If no custom filename, use a standard format
            default_output_path = os.path.join(output_dir, f"instagram_{shortcode}.mp4")
            if os.path.exists(default_output_path):
                os.remove(default_output_path)
            shutil.move(temp_video_path, default_output_path)
            print(f"✅ Video saved with default name: {default_output_path}")
            # Clean up temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)
            return default_output_path
        
    except instaloader.exceptions.InstaloaderException as e:
        print(f"❌ Instaloader error: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None
    finally:
        # Make sure temp directory is cleaned up
        if 'temp_dir' in locals() and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)