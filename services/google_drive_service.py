import io
import os
from typing import List
from dataclasses import dataclass
from datetime import datetime
from abc import ABC, abstractmethod
from googleapiclient.http import MediaFileUpload

@dataclass
class FileInfo:
    """Data class for file information."""
    id: str
    name: str
    type: str
    modified: str
    is_folder: bool

@dataclass
class FolderPath:
    """Data class for folder path information."""
    id: str
    name: str

class GoogleDriveError(Exception):
    """Base exception for Google Drive operations."""
    pass

class FileOperationError(GoogleDriveError):
    """Exception for file operation errors."""
    pass

class FolderOperationError(GoogleDriveError):
    """Exception for folder operation errors."""
    pass

class FileMetadataError(GoogleDriveError):
    """Exception for file metadata errors."""
    pass

class FileOperation(ABC):
    """Abstract base class for file operations."""
    
    @abstractmethod
    def upload(self, file_path: str, folder_id: str = 'root') -> str:
        """Upload a file to Google Drive.
        
        Args:
            file_path: Path to the file to upload
            folder_id: ID of the folder to upload to (default: 'root')
            
        Returns:
            str: ID of the uploaded file
            
        Raises:
            FileOperationError: If upload fails
        """
        pass
        
    @abstractmethod
    def download(self, file_id: str) -> io.BytesIO:
        """Download a file from Google Drive.
        
        Args:
            file_id: ID of the file to download
            
        Returns:
            io.BytesIO: File content as bytes
            
        Raises:
            FileOperationError: If download fails
        """
        pass
        
    @abstractmethod
    def delete(self, file_id: str) -> None:
        """Delete a file from Google Drive.
        
        Args:
            file_id: ID of the file to delete
            
        Raises:
            FileOperationError: If deletion fails
        """
        pass

class FolderOperation(ABC):
    """Abstract base class for folder operations."""
    
    @abstractmethod
    def get_name(self, folder_id: str) -> str:
        """Get the name of a folder.
        
        Args:
            folder_id: ID of the folder
            
        Returns:
            str: Name of the folder
            
        Raises:
            FolderOperationError: If operation fails
        """
        pass
        
    @abstractmethod
    def get_path(self, folder_id: str) -> List[FolderPath]:
        """Get the path to a folder.
        
        Args:
            folder_id: ID of the folder
            
        Returns:
            List[FolderPath]: List of folders in the path
            
        Raises:
            FolderOperationError: If operation fails
        """
        pass

class FileMetadata(ABC):
    """Abstract base class for file metadata operations."""
    
    @abstractmethod
    def get_name(self, file_id: str) -> str:
        """Get the name of a file.
        
        Args:
            file_id: ID of the file
            
        Returns:
            str: Name of the file
            
        Raises:
            FileMetadataError: If operation fails
        """
        pass
        
    @abstractmethod
    def get_parent(self, file_id: str) -> str:
        """Get the parent folder ID of a file.
        
        Args:
            file_id: ID of the file
            
        Returns:
            str: ID of the parent folder
            
        Raises:
            FileMetadataError: If operation fails
        """
        pass

class GoogleDriveFileOperation(FileOperation):
    """Concrete implementation of file operations."""
    
    def __init__(self, service):
        self.service = service
    
    def upload(self, file_path: str, folder_id: str = 'root') -> str:
        try:
            if not os.path.exists(file_path):
                raise FileOperationError(f"File not found: {file_path}")
                
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
        except Exception as e:
            raise FileOperationError(f"Failed to upload file: {str(e)}")
    
    def download(self, file_id: str) -> io.BytesIO:
        try:
            request = self.service.files().get_media(fileId=file_id)
            content = request.execute()
            file = io.BytesIO(content)
            return file
        except Exception as e:
            raise FileOperationError(f"Failed to download file: {str(e)}")
    
    def delete(self, file_id: str) -> None:
        try:
            self.service.files().delete(fileId=file_id).execute()
        except Exception as e:
            raise FileOperationError(f"Failed to delete file: {str(e)}")

class GoogleDriveFolderOperation(FolderOperation):
    """Concrete implementation of folder operations."""
    
    def __init__(self, service):
        self.service = service
    
    def get_name(self, folder_id: str) -> str:
        if folder_id == 'root':
            return "Root"
            
        try:
            folder = self.service.files().get(
                fileId=folder_id,
                fields="name"
            ).execute()
            return folder.get('name', 'Unknown Folder')
        except Exception as e:
            raise FolderOperationError(f"Failed to get folder name: {str(e)}")
    
    def get_path(self, folder_id: str) -> List[FolderPath]:
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
                
                path.insert(0, FolderPath(
                    id=file['id'],
                    name=file['name']
                ))
                
                parents = file.get('parents', [])
                if parents:
                    current_id = parents[0]
                else:
                    break
            except Exception as e:
                raise FolderOperationError(f"Failed to get folder path: {str(e)}")
                
        return path

class GoogleDriveFileMetadata(FileMetadata):
    """Concrete implementation of file metadata operations."""
    
    def __init__(self, service):
        self.service = service
    
    def get_name(self, file_id: str) -> str:
        try:
            file = self.service.files().get(
                fileId=file_id,
                fields="name"
            ).execute()
            return file.get('name', 'Unknown File')
        except Exception as e:
            raise FileMetadataError(f"Failed to get file name: {str(e)}")
    
    def get_parent(self, file_id: str) -> str:
        try:
            file = self.service.files().get(
                fileId=file_id,
                fields="parents"
            ).execute()
            return file.get('parents', ['root'])[0]
        except Exception as e:
            raise FileMetadataError(f"Failed to get parent folder: {str(e)}")

class GoogleDriveService:
    """Service class that coordinates different Google Drive operations."""
    
    def __init__(self, service):
        self.file_operation = GoogleDriveFileOperation(service)
        self.folder_operation = GoogleDriveFolderOperation(service)
        self.file_metadata = GoogleDriveFileMetadata(service)
        self.service = service
    
    def list_files(self, folder_id: str = 'root', page_size: int = 50) -> List[FileInfo]:
        """List files and folders in a directory.
        
        Args:
            folder_id: ID of the folder to list (default: 'root')
            page_size: Number of items per page (default: 50)
            
        Returns:
            List[FileInfo]: List of files and folders
            
        Raises:
            GoogleDriveError: If operation fails
        """
        try:
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
                
                file_info = FileInfo(
                    id=file['id'],
                    name=file['name'],
                    type=file['mimeType'],
                    modified=modified_time.strftime('%Y-%m-%d %H:%M:%S'),
                    is_folder=is_folder
                )
                file_list.append(file_info)
                
            return file_list
        except Exception as e:
            raise GoogleDriveError(f"Failed to list files: {str(e)}")
    
    def get_folder_name(self, folder_id: str) -> str:
        return self.folder_operation.get_name(folder_id)
    
    def get_folder_path(self, folder_id: str) -> List[FolderPath]:
        return self.folder_operation.get_path(folder_id)
    
    def upload_file(self, file_path: str, folder_id: str = 'root') -> str:
        return self.file_operation.upload(file_path, folder_id)
    
    def download_file(self, file_id: str) -> io.BytesIO:
        return self.file_operation.download(file_id)
    
    def get_file_name(self, file_id: str) -> str:
        return self.file_metadata.get_name(file_id)
    
    def get_file_parent(self, file_id: str) -> str:
        return self.file_metadata.get_parent(file_id)
    
    def delete_file(self, file_id: str) -> None:
        self.file_operation.delete(file_id) 