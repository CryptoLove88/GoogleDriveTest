from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from datetime import datetime
import io
import os

class GoogleDrive:
    """Class to handle Google Drive operations."""
    
    def __init__(self, service):
        """Initialize with Google Drive service."""
        self.service = service
    
    def list_files(self, folder_id='root', page_size=50):
        """List files and folders in a directory."""
        query = f"'{folder_id}' in parents and trashed = false"
        results = self.service.files().list(
            q=query,
            pageSize=page_size,
            fields="nextPageToken, files(id, name, mimeType, modifiedTime)",
            orderBy="folder,name"
        ).execute()
        
        files = results.get('files', [])
        file_list = []
        
        for file in files:
            modified_time = datetime.fromisoformat(file['modifiedTime'].replace('Z', '+00:00'))
            is_folder = file['mimeType'] == 'application/vnd.google-apps.folder'
            
            file_info = {
                'id': file['id'],
                'name': file['name'],
                'type': file['mimeType'],
                'modified': modified_time.strftime('%Y-%m-%d %H:%M:%S'),
                'is_folder': is_folder
            }
            file_list.append(file_info)
            
        return file_list
    
    def get_folder_name(self, folder_id):
        """Get the name of a folder."""
        if folder_id == 'root':
            return "Root"
            
        try:
            folder = self.service.files().get(
                fileId=folder_id,
                fields="name"
            ).execute()
            return folder.get('name', 'Unknown Folder')
        except Exception as e:
            print(f"Error getting folder name: {str(e)}")
            return "Unknown Folder"
    
    def get_folder_path(self, folder_id):
        """Get the path to a folder."""
        if folder_id == 'root':
            return []
            
        path = []
        current_id = folder_id
        
        while current_id != 'root':
            try:
                file = self.service.files().get(
                    fileId=current_id,
                    fields="id, name, parents"
                ).execute()
                
                path.insert(0, {
                    'id': file['id'],
                    'name': file['name']
                })
                
                parents = file.get('parents', [])
                if parents:
                    current_id = parents[0]
                else:
                    break
            except Exception as e:
                print(f"Error getting parent folder: {str(e)}")
                break
                
        return path
    
    def upload_file(self, file_path, folder_id='root'):
        """Upload a file to Google Drive."""
        file_metadata = {
            'name': os.path.basename(file_path),
            'parents': [folder_id]
        }
        
        media = MediaFileUpload(
            file_path,
            resumable=True
        )
        
        file = self.service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        return file.get('id')
    
    def download_file(self, file_id):
        """Download a file from Google Drive."""
        request = self.service.files().get_media(fileId=file_id)
        file = io.BytesIO()
        downloader = MediaIoBaseDownload(file, request)
        
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        
        file.seek(0)
        return file
    
    def get_file_name(self, file_id):
        """Get the name of a file."""
        try:
            file = self.service.files().get(
                fileId=file_id,
                fields="name"
            ).execute()
            return file.get('name', 'Unknown File')
        except Exception as e:
            print(f"Error getting file name: {str(e)}")
            return "Unknown File"
    
    def delete_file(self, file_id):
        """Delete a file from Google Drive."""
        self.service.files().delete(fileId=file_id).execute() 