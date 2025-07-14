import os
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

class TokenManager:
    """A class to manage OAuth tokens for Google APIs."""
    
    def __init__(self, token_file, scopes, credentials_file='credentials.json'):
        """
        Initialize the TokenManager.
        
        Args:
            token_file: Path to the token file
            scopes: List of OAuth scopes required
            credentials_file: Path to the credentials.json file
        """
        self.token_file = token_file
        self.scopes = scopes
        self.credentials_file = credentials_file
        self.creds = None
    
    def load_token(self):
        """Load token from file and check if valid."""
        if os.path.exists(self.token_file):
            try:
                self.creds = Credentials.from_authorized_user_file(self.token_file, self.scopes)
                return self.creds
            except Exception as e:
                print(f"Error loading token from {self.token_file}: {e}")
                # If token file is corrupted, handle by treating as no token
                self.creds = None
        return None
    
    def refresh_token(self):
        """Refresh the token if expired."""
        if not self.creds:
            self.load_token()
            
        if not self.creds:
            return self.create_new_token()
            
        if not self.creds.valid:
            if self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                    self.save_token()
                    return self.creds
                except Exception as e:
                    print(f"Error refreshing token: {e}")
                    # If refresh fails, fallback to creating a new token
                    return self.create_new_token()
            else:
                return self.create_new_token()
        
        return self.creds
    
    def create_new_token(self):
        """Create a new token via user authorization."""
        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                self.credentials_file, 
                self.scopes
            )
            self.creds = flow.run_local_server(port=0)
            self.save_token()
            return self.creds
        except Exception as e:
            print(f"Error creating new token: {e}")
            raise
    
    def save_token(self):
        """Save the token to file."""
        if self.creds:
            try:
                with open(self.token_file, 'w') as token:
                    token.write(self.creds.to_json())
                print(f"Token saved to {self.token_file}")
            except Exception as e:
                print(f"Error saving token to {self.token_file}: {e}")
    
    def get_credentials(self):
        """Get valid credentials, refreshing if necessary."""
        if not self.creds:
            self.load_token()
            
        if not self.creds or not self.creds.valid:
            self.refresh_token()
            
        return self.creds
    
    def build_service(self, api_name, api_version):
        """Build and return a service for the specified API."""
        creds = self.get_credentials()
        return build(api_name, api_version, credentials=creds)


# Utility functions for common APIs
def get_youtube_service():
    """Get authenticated YouTube service."""
    scopes = [
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube"
    ]
    token_manager = TokenManager("youtube_token.json", scopes)
    return token_manager.build_service("youtube", "v3")

def get_gmail_service(full_access=False):
    """
    Get authenticated Gmail service.
    
    Args:
        full_access: If True, use full mail.google.com scope for deletion, 
                    otherwise use modify scope for reading
    """
    if full_access:
        scopes = ['https://mail.google.com/']
        token_file = 'gmail_deletion_token.json'
    else:
        scopes = ['https://www.googleapis.com/auth/gmail.modify']
        token_file = 'token.json'
        
    token_manager = TokenManager(token_file, scopes)
    return token_manager.build_service("gmail", "v1")
