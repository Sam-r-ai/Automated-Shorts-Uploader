# Automated-Shorts-Uploader
Send email of link to video and it gets automatically uploaded to my shorts channel

This project demonstrates how to use the Gmail API to authenticate and monitor emails programmatically. It includes setting up the Gmail API, authenticating, and fetching emails from a specific sender.

## **Setup Instructions**

### **1. Prerequisites**
1. Install Python 3.x on your system.
   Install required Python libraries:
   ```bash
   pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
   
2. Google Cloud Project Setup
Create a New Project:

Go to Google Cloud Console.
Create a new project.
Enable Gmail API:

Navigate to APIs & Services > Library.
Search for "Gmail API" and enable it.
Set Up OAuth Consent Screen:

Go to APIs & Services > OAuth consent screen.
Choose "External" for the user type and fill in the required details.
Add the email address you’ll use for testing under Test Users.
Create OAuth 2.0 Credentials:

Go to APIs & Services > Credentials.
Click Create Credentials > OAuth 2.0 Client ID.
Application type: Desktop App.
Download the resulting JSON file and save it as credentials.json in the project directory.

3. Project Setup
Clone or download the repository:

bash
Copy code
git clone <repository-url>
cd <repository-directory>
Place the credentials.json file in the project directory.

Run the script to authenticate:

bash
Copy code
python AuthenticateEmail.py
During the first run:

A browser will open asking for permission to access your Gmail.
Complete the authentication process.
A token.json file will be created to store the access and refresh tokens.

4. Fetching Emails
Modify the AuthenticateEmail.py script to customize email queries:
Change the sender email address (justinferrari91@gmail.com) or add additional filters.
Run the script to continuously monitor for emails:
bash
Copy code
python AuthenticateEmail.py

6. Notes
The token.json file is reused for future authentications, so you don’t need to log in again.
Ensure the credentials.json and token.json files are stored securely and not shared publicly.
