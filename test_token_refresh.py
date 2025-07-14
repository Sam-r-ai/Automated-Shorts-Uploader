import os
import sys
from token_manager import TokenManager, get_youtube_service, get_gmail_service

def test_youtube_token():
    """Test YouTube token refresh."""
    print("Testing YouTube token...")
    try:
        youtube = get_youtube_service()
        # Test a simple API call to verify the token
        response = youtube.channels().list(
            part="snippet",
            mine=True
        ).execute()
        
        if 'items' in response:
            channel_name = response['items'][0]['snippet']['title']
            print(f"✅ YouTube authentication successful! Connected to channel: {channel_name}")
        else:
            print("✅ YouTube authentication successful, but no channel found.")
        
        return True
    except Exception as e:
        print(f"❌ YouTube authentication failed: {e}")
        return False

def test_gmail_token(full_access=False):
    """Test Gmail token refresh."""
    scope_type = "full access" if full_access else "modify access"
    print(f"Testing Gmail token with {scope_type}...")
    try:
        gmail = get_gmail_service(full_access=full_access)
        # Test a simple API call to verify the token
        profile = gmail.users().getProfile(userId='me').execute()
        
        if 'emailAddress' in profile:
            print(f"✅ Gmail authentication successful! Connected to: {profile['emailAddress']}")
        else:
            print("✅ Gmail authentication successful, but no email address found.")
        
        return True
    except Exception as e:
        print(f"❌ Gmail authentication failed: {e}")
        return False

def test_token_manager():
    """Run all token tests."""
    print("=" * 50)
    print("TOKEN MANAGER TEST")
    print("=" * 50)
    
    # Test individual token file loading and refreshing
    youtube_scopes = [
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube"
    ]
    gmail_scopes = ['https://www.googleapis.com/auth/gmail.modify']
    gmail_full_scopes = ['https://mail.google.com/']
    
    print("\nTesting direct TokenManager usage:")
    
    # Test YouTube token
    print("\nTesting YouTube token directly...")
    yt_manager = TokenManager("youtube_token.json", youtube_scopes)
    try:
        creds = yt_manager.get_credentials()
        print(f"✅ YouTube token {'valid' if creds.valid else 'invalid'}")
    except Exception as e:
        print(f"❌ YouTube token error: {e}")
    
    # Test Gmail token
    print("\nTesting Gmail token directly...")
    gmail_manager = TokenManager("token.json", gmail_scopes)
    try:
        creds = gmail_manager.get_credentials()
        print(f"✅ Gmail token {'valid' if creds.valid else 'invalid'}")
    except Exception as e:
        print(f"❌ Gmail token error: {e}")
    
    # Test helper functions
    print("\nTesting helper functions:")
    test_youtube_token()
    test_gmail_token(full_access=False)
    test_gmail_token(full_access=True)
    
    print("\nAll tests completed!")

if __name__ == "__main__":
    test_token_manager()
