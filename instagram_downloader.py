import instaloader
import os
import re
import time
import random
import shutil

def download_instagram_reel(url, output_dir=None, custom_filename=None):
    """
    Download Instagram reel video using instaloader library
    """
    # Set default output directory if not provided
    if not output_dir:
        output_dir = os.path.join(os.path.expanduser("~"), "Downloads")

    os.makedirs(output_dir, exist_ok=True)

    # Extract shortcode from URL
    shortcode_match = re.search(r'/(p|reel|tv)/([^/?]+)', url)
    if not shortcode_match:
        print(f"❌ Invalid Instagram URL: {url}")
        return None

    shortcode = shortcode_match.group(2)
    print(f"📋 Extracted shortcode: {shortcode}")

    # Custom filename logic
    final_output_path = None
    if custom_filename:
        if not custom_filename.endswith('.mp4'):
            custom_filename += '.mp4'
        final_output_path = os.path.join(output_dir, custom_filename)

        if os.path.exists(final_output_path) and os.path.getsize(final_output_path) > 0:
            print(f"✅ File already exists: {final_output_path}")
            return final_output_path

    # Initialize Instaloader
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
        # Anti-rate-limit delay
        delay = random.uniform(2, 5)
        print(f"⏳ Waiting {delay:.1f}s...")
        time.sleep(delay)

        # Fetch post
        print(f"⏱️ Downloading reel: {shortcode}")
        post = instaloader.Post.from_shortcode(L.context, shortcode)

        # Temp directory
        temp_dir = os.path.join(output_dir, f"temp_{shortcode}_{int(time.time())}")
        os.makedirs(temp_dir, exist_ok=True)

        L.dirname_pattern = temp_dir
        L.download_post(post, target=shortcode)

        # Find temp .mp4
        temp_video_path = None
        for f in os.listdir(temp_dir):
            if f.endswith(".mp4"):
                temp_video_path = os.path.join(temp_dir, f)
                break

        if not temp_video_path:
            print("⚠️ No video file found after download")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return None

        # Move to final path
        if final_output_path:
            if os.path.exists(final_output_path):
                os.remove(final_output_path)
            shutil.move(temp_video_path, final_output_path)
            print(f"✅ Saved as: {final_output_path}")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return final_output_path
        else:
            default_output = os.path.join(output_dir, f"instagram_{shortcode}.mp4")
            if os.path.exists(default_output):
                os.remove(default_output)
            shutil.move(temp_video_path, default_output)
            print(f"✅ Saved as: {default_output}")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return default_output

    except instaloader.exceptions.InstaloaderException as e:
        print(f"❌ Instaloader error: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None
    finally:
        # Cleanup
        if 'temp_dir' in locals() and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


# ----------------------------------------------------------
# ✅ MAIN FUNCTION FOR TESTING
# ----------------------------------------------------------
def main():
    print("\n=== Instagram Reel Downloader Test ===\n")
    url = input("Paste Instagram Reel URL: ").strip()

    print("\nDownloading...\n")
    result = download_instagram_reel(url)

    if result:
        print(f"\n🎉 DONE! File saved at:\n{result}\n")
    else:
        print("\n❌ FAILED to download.\n")


if __name__ == "__main__":
    main()
