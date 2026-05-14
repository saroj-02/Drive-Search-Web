import os
import time
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

class DriveService:
    def __init__(self):
        self.scopes = ['https://www.googleapis.com/auth/drive.readonly']
        self.service_account_file = os.getenv('SERVICE_ACCOUNT_FILE', 'service_account.json')
        self.folder_id = os.getenv('DRIVE_FOLDER_ID')
        self.creds = None
        self.service = None
        
        if os.path.exists(self.service_account_file):
            self.creds = service_account.Credentials.from_service_account_file(
                self.service_account_file, scopes=self.scopes
            )
            self.service = build('drive', 'v3', credentials=self.creds)

    def search_files(self, query_string=None, name=None, mime_type=None, full_text=None):
        """
        Search for files in the designated folder using the Drive API's q parameter.
        """
        if not self.service:
            return "Error: Google Drive service not initialized. Please check service_account.json."

        q_parts = [f"'{self.folder_id}' in parents"] if self.folder_id else []
        
        # If no folder_id is provided, search globally in Drive (within the account's access)
        if not self.folder_id and not query_string and not name and not full_text:
            return "Please provide a search term or a Folder ID to start searching."

        if name:
            q_parts.append(f"name contains '{name}'")
        if mime_type:
            q_parts.append(f"mimeType = '{mime_type}'")
        if full_text:
            q_parts.append(f"fullText contains '{full_text}'")
        if query_string:
            q_parts.append(query_string)

        q = " and ".join(q_parts)
        
        try:
            results = self.service.files().list(
                q=q,
                spaces='drive',
                fields='nextPageToken, files(id, name, mimeType, webViewLink, modifiedTime, size)',
                pageSize=10
            ).execute()
            return results.get('files', [])
        except Exception as e:
            return f"Error searching files: {str(e)}"

    def get_file_metadata(self, file_id):
        """Get detailed metadata for a specific file."""
        if not self.service:
            return None
        try:
            return self.service.files().get(fileId=file_id, fields='id, name, mimeType, description, webViewLink, modifiedTime, size').execute()
        except Exception as e:
            return f"Error getting metadata: {str(e)}"

    def list_folders(self):
        """List all folders in the drive."""
        if not self.service:
            return "Error: Google Drive service not initialized."
        
        try:
            results = self.service.files().list(
                q="mimeType = 'application/vnd.google-apps.folder' and trashed = false",
                spaces='drive',
                fields='nextPageToken, files(id, name)',
                pageSize=100
            ).execute()
            return results.get('files', [])
        except Exception as e:
            return f"Error listing folders: {str(e)}"

class LocalService:
    def __init__(self):
        self.root_path = None

    def search_files(self, query=None, name=None, mime_type=None, max_depth=3):
        """Search for files in the local directory with a depth limit."""
        if not self.root_path or not os.path.exists(self.root_path):
            return "Error: Local path not set or does not exist."
        
        matches = []
        base_depth = self.root_path.rstrip(os.path.sep).count(os.path.sep)
        
        try:
            for root, dirs, files in os.walk(self.root_path):
                # Check depth
                current_depth = root.rstrip(os.path.sep).count(os.path.sep)
                if current_depth - base_depth > max_depth:
                    # Don't descend deeper, but can still process files in this directory
                    dirs[:] = [] # Clear dirs to prevent further descent
                    
                for file in files:
                    full_path = os.path.join(root, file)
                    # Simple matching logic
                    match = True
                    if name and name.lower() not in file.lower():
                        match = False
                    if query and query.lower() not in file.lower():
                        match = False
                    
                    if match:
                        matches.append({
                            'id': full_path,
                            'name': file,
                            'mimeType': 'file',
                            'path': full_path
                        })
                        if len(matches) >= 10: break
                if len(matches) >= 10: break
            return matches
        except Exception as e:
            return f"Error searching local files: {str(e)}"

    def get_file_metadata(self, file_path):
        """Get local file metadata."""
        if not os.path.exists(file_path):
            return "File not found."
        try:
            stats = os.stat(file_path)
            return {
                'name': os.path.basename(file_path),
                'mimeType': 'file',
                'modifiedTime': time.ctime(stats.st_mtime),
                'size': stats.st_size,
                'path': file_path
            }
        except Exception as e:
            return f"Error: {str(e)}"

drive_service = DriveService()
local_service = LocalService()
