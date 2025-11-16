from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os
import requests

def get_video_url(instagram_url):
    """Extract the video URL from Instagram Reel."""
    # Path to ChromeDriver
    chrome_driver_path = r"C:\chromedriver-win64\chromedriver.exe"  # Update this if needed

    # Set Chrome options for mobile emulation
    mobile_emulation = {"deviceName": "Nexus 5"}
    chrome_options = Options()
    chrome_options.add_experimental_option("mobileEmulation", mobile_emulation)
    chrome_options.add_argument("--headless=new")  # More stable headless mode
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--enable-unsafe-swiftshader")
    # Start WebDriver
    service = Service(chrome_driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        print(f"Opening Instagram Reel: {instagram_url}")
        driver.get(instagram_url)  # **This was missing**

        # Wait for the video element to appear
        video_element = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "video"))
        )
        video_url = video_element.get_attribute("src")

        if video_url:
            print(f"Extracted Video URL: {video_url}")
            return video_url
        else:
            print("❌ Video URL not found.")
            return None
    except Exception as e:
        print(f"⚠️ Error extracting video: {e}")
        return None
    finally:
        driver.quit()

def download_video(video_url, output_filename="instagram_video.mp4"):
    """Download video from the extracted URL."""
    downloads_folder = r"C:\Users\super\Downloads"
    output_path = os.path.join(downloads_folder, output_filename)

    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Mobile Safari/537.36",
        "Referer": "https://www.instagram.com/"
    }

    response = requests.get(video_url, headers=headers, stream=True)
    if response.status_code == 200:
        with open(output_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=1024):
                file.write(chunk)
        print(f"✅ Video downloaded successfully to {output_path}")
    else:
        print(f"❌ Failed to download video. Status code: {response.status_code}")

if __name__ == "__main__":
    # Instagram Reel URL
    reel_url = "https://www.instagram.com/reel/DHMcHelxXpB/?igsh=NjZiM2M3MzIxNA=="

    # Step 1: Extract video URL
    video_url = get_video_url(reel_url)

    # Step 2: Download the video
    if video_url:
        output_file = "instagram_video.mp4"
        download_video(video_url, output_file)
    else:
        print("❌ No video URL extracted, skipping download.")
