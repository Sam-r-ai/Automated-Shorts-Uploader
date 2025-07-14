import os
import time
from dotenv import load_dotenv
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

load_dotenv()
# Define the scope for Gmail API (full access needed for deletion)
SCOPES = ['https://mail.google.com/']  # Full access scope required for batch delete

def authenticate_gmail():
    """Authenticate with Gmail API and return the service object."""
    try:
        # Use the token manager to get an authenticated service with full access
        from token_manager import get_gmail_service
        return get_gmail_service(full_access=True)
    except Exception as e:
        print(f"Error authenticating Gmail for deletion: {e}")
        # Fallback to legacy authentication if the token manager fails
        creds = None
        # Force token refresh by checking for special deletion token first
        if os.path.exists('gmail_deletion_token.json'):
            creds = Credentials.from_authorized_user_file('gmail_deletion_token.json', SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                # Create a new flow with the more permissive scope
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            # Save token separately to avoid interfering with other scripts
            with open('gmail_deletion_token.json', 'w') as token:
                token.write(creds.to_json())
        return build('gmail', 'v1', credentials=creds)

def delete_emails(service, sender_email, batch_size=100, max_emails=1000):
    """
    Delete all emails from a specific sender.
    
    Args:
        service: Gmail API service instance
        sender_email: Email address to filter by
        batch_size: Number of emails to delete in each batch
        max_emails: Maximum number of emails to delete (safety limit)
        
    Returns:
        Total number of emails deleted
    """
    query = f"from:{sender_email}"
    deleted_count = 0
    
    print(f"Looking for emails from {sender_email}...")
    
    # Get all matching emails
    results = service.users().messages().list(userId='me', q=query, maxResults=max_emails).execute()
    messages = results.get('messages', [])
    
    if not messages:
        print("No emails found from this sender.")
        return 0
    
    total_messages = len(messages)
    print(f"Found {total_messages} emails to delete.")
    
    # Process deletion in batches
    for i in range(0, total_messages, batch_size):
        batch = messages[i:i+batch_size]
        batch_ids = [msg['id'] for msg in batch]
        
        # Perform batch deletion
        try:
            batch_request = {
                'ids': batch_ids
            }
            service.users().messages().batchDelete(userId='me', body=batch_request).execute()
            deleted_count += len(batch)
            print(f"Deleted batch of {len(batch)} emails. Progress: {deleted_count}/{total_messages}")
            
            # Brief pause to avoid rate limits
            time.sleep(1)
            
        except Exception as e:
            print(f"Error deleting batch: {e}")
            # Try trashing individual emails if batch delete fails
            try:
                print("Attempting to trash emails individually instead...")
                individual_success = 0
                for msg_id in batch_ids:
                    try:
                        service.users().messages().trash(userId='me', id=msg_id).execute()
                        individual_success += 1
                        # More aggressive rate limiting for individual calls
                        time.sleep(0.5)
                    except Exception as inner_e:
                        print(f"  Failed to trash message {msg_id}: {inner_e}")
                
                if individual_success > 0:
                    print(f"  Successfully trashed {individual_success} out of {len(batch)} emails")
                    deleted_count += individual_success
            except Exception as fallback_e:
                print(f"  Fallback trash method also failed: {fallback_e}")
            
    print(f"Deletion complete. Removed {deleted_count} emails from {sender_email}.")
    return deleted_count

def main():
    """Main function to run the email deletion tool."""
    # Sender email to target for deletion
    sender_email = os.getenv("SENDER_EMAIL")  # Use the environment variable from .env file
    print("=====================================================")
    print("Gmail Cleanup Tool - Email Deletion Utility")
    print("=====================================================")
    
    if(sender_email == "" or sender_email is None):
        print("Error: Sender email is not set. Please set the sender_email variable.")
        exit(1)

    # Get Gmail service
    print("Authenticating with Gmail...")
    gmail_service = authenticate_gmail()
    print("Authentication successful!")
    
    # Confirm before deletion
    print(f"\nThis will delete ALL emails from {sender_email}")
    print("NOTE: You will need to re-authorize with FULL Gmail access")
    print("      A browser window will open for authorization")
    confirm = input("\nAre you sure you want to proceed? (yes/no): ")
    
    if confirm.lower() in ['yes', 'y']:
        print("\nStarting deletion process...")
        # Delete emails
        delete_count = delete_emails(gmail_service, sender_email)
        print(f"\nOperation complete. {delete_count} emails deleted.")
    else:
        print("\nOperation cancelled.")

if __name__ == '__main__':
    main()
