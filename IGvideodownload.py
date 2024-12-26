from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time
import os

def get_video_url(instagram_url):
    """Extract the video URL from Instagram Reel."""
    # Path to ChromeDriver
    chrome_driver_path = r"C:\chromedriver-win64\chromedriver.exe"  # Replace with your actual path

    # Set Chrome options for mobile emulation
    mobile_emulation = {"deviceName": "Nexus 5"}
    chrome_options = Options()
    chrome_options.add_experimental_option("mobileEmulation", mobile_emulation)
    chrome_options.add_argument("--headless")  # Optional: run in headless mode
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-dev-shm-usage")

    # Start WebDriver
    service = Service(chrome_driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        # Open Instagram Reel URL
        driver.get(instagram_url)
        time.sleep(5)  # Wait for the page to load

        # Locate the <video> tag in the mobile emulation mode
        video_element = driver.find_element(By.TAG_NAME, "video")
        video_url = video_element.get_attribute("src")

        print(f"Video URL: {video_url}")
        return video_url
    except Exception as e:
        print(f"Error: {e}")
        return None
    finally:
        driver.quit()

def download_video(video_url, output_filename="instagram_video.mp4"):
    """Download video from the extracted URL."""
    import requests

    # Ensure the video is downloaded to the Downloads folder
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
        print(f"Video downloaded successfully to {output_path}")
    else:
        print(f"Failed to download video. Status code: {response.status_code}")

if __name__ == "__main__":
    # Instagram Reel URL
    reel_url = input("Enter the Instagram Reel URL: ")

    # Step 1: Extract video URL
    video_url = get_video_url(reel_url)

    # Step 2: Download the video
    if video_url:
        output_file = input("Enter the output filename (default: instagram_video.mp4): ") or "instagram_video.mp4"
        
        # Ensure the output filename ends with .mp4
        if not output_file.lower().endswith(".mp4"):
            output_file += ".mp4"
        
        download_video(video_url, output_file)
