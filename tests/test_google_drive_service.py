import unittest
from unittest.mock import Mock, patch
from datetime import datetime
import io
import os
from services.google_drive_service import (
    GoogleDriveService,
    GoogleDriveFileOperation,
    GoogleDriveFolderOperation,
    GoogleDriveFileMetadata,
    FileInfo,
    FolderPath,
    GoogleDriveError,
    FileOperationError,
    FolderOperationError,
    FileMetadataError
)

class TestGoogleDriveFileOperation(unittest.TestCase):
    def setUp(self):
        self.mock_service = Mock()
        self.file_operation = GoogleDriveFileOperation(self.mock_service)
        
    def test_upload_success(self):
        # Mock the file creation response
        mock_response = {'id': 'test_file_id'}
        self.mock_service.files().create().execute.return_value = mock_response
        
        # Create a temporary test file
        test_file_path = 'test_upload.txt'
        with open(test_file_path, 'w') as f:
            f.write('test content')
            
        try:
            result = self.file_operation.upload(test_file_path)
            self.assertEqual(result, 'test_file_id')
            self.mock_service.files().create.assert_called()
        finally:
            # Clean up
            if os.path.exists(test_file_path):
                os.remove(test_file_path)
                
    def test_upload_file_not_found(self):
        with self.assertRaises(FileOperationError):
            self.file_operation.upload('nonexistent_file.txt')
            
    def test_download_success(self):
        # Mock the file content
        mock_content = b'test content'
        
        # Mock the get_media method to return a request object
        mock_request = Mock()
        mock_request.execute.return_value = mock_content
        self.mock_service.files().get_media.return_value = mock_request
        
        result = self.file_operation.download('test_file_id')
        self.assertIsInstance(result, io.BytesIO)
        self.assertEqual(result.getvalue(), mock_content)
        self.mock_service.files().get_media.assert_called_once_with(fileId='test_file_id')
        
    def test_delete_success(self):
        self.file_operation.delete('test_file_id')
        self.mock_service.files().delete.assert_called_once_with(fileId='test_file_id')

class TestGoogleDriveFolderOperation(unittest.TestCase):
    def setUp(self):
        self.mock_service = Mock()
        self.folder_operation = GoogleDriveFolderOperation(self.mock_service)
        
    def test_get_name_root(self):
        result = self.folder_operation.get_name('root')
        self.assertEqual(result, 'Root')
        
    def test_get_name_success(self):
        mock_response = {'name': 'Test Folder'}
        self.mock_service.files().get().execute.return_value = mock_response
        
        result = self.folder_operation.get_name('test_folder_id')
        self.assertEqual(result, 'Test Folder')
        self.mock_service.files().get.assert_called()
        
    def test_get_path_root(self):
        result = self.folder_operation.get_path('root')
        self.assertEqual(result, [])
        
    def test_get_path_success(self):
        # Mock the folder hierarchy
        mock_responses = [
            {'id': 'parent_id', 'name': 'Parent', 'parents': ['root']},
            {'id': 'child_id', 'name': 'Child', 'parents': ['parent_id']}
        ]
        self.mock_service.files().get().execute.side_effect = mock_responses
        
        result = self.folder_operation.get_path('child_id')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, 'Parent')

class TestGoogleDriveFileMetadata(unittest.TestCase):
    def setUp(self):
        self.mock_service = Mock()
        self.file_metadata = GoogleDriveFileMetadata(self.mock_service)
        
    def test_get_name_success(self):
        mock_response = {'name': 'test_file.txt'}
        self.mock_service.files().get().execute.return_value = mock_response
        
        result = self.file_metadata.get_name('test_file_id')
        self.assertEqual(result, 'test_file.txt')
        
    def test_get_parent_success(self):
        mock_response = {'parents': ['parent_folder_id']}
        self.mock_service.files().get().execute.return_value = mock_response
        
        result = self.file_metadata.get_parent('test_file_id')
        self.assertEqual(result, 'parent_folder_id')

class TestGoogleDriveService(unittest.TestCase):
    def setUp(self):
        self.mock_service = Mock()
        self.drive_service = GoogleDriveService(self.mock_service)
        
    def test_list_files_success(self):
        # Mock the file list response
        mock_files = [
            {
                'id': 'file1',
                'name': 'test1.txt',
                'mimeType': 'text/plain',
                'modifiedTime': '2024-01-01T00:00:00Z'
            },
            {
                'id': 'folder1',
                'name': 'test_folder',
                'mimeType': 'application/vnd.google-apps.folder',
                'modifiedTime': '2024-01-01T00:00:00Z'
            }
        ]
        mock_response = {'files': mock_files}
        self.mock_service.files().list().execute.return_value = mock_response
        
        result = self.drive_service.list_files()
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], FileInfo)
        self.assertTrue(result[1].is_folder)
        
    def test_upload_file_success(self):
        # Create a temporary test file
        test_file_path = 'test_upload.txt'
        with open(test_file_path, 'w') as f:
            f.write('test content')
            
        try:
            with patch.object(self.drive_service.file_operation, 'upload') as mock_upload:
                mock_upload.return_value = 'test_file_id'
                result = self.drive_service.upload_file(test_file_path)
                self.assertEqual(result, 'test_file_id')
                mock_upload.assert_called_once_with(test_file_path, 'root')
        finally:
            if os.path.exists(test_file_path):
                os.remove(test_file_path)
                
    def test_download_file_success(self):
        with patch.object(self.drive_service.file_operation, 'download') as mock_download:
            mock_download.return_value = io.BytesIO(b'test content')
            result = self.drive_service.download_file('test_file_id')
            self.assertIsInstance(result, io.BytesIO)
            mock_download.assert_called_once_with('test_file_id')
            
    def test_delete_file_success(self):
        with patch.object(self.drive_service.file_operation, 'delete') as mock_delete:
            self.drive_service.delete_file('test_file_id')
            mock_delete.assert_called_once_with('test_file_id')

if __name__ == '__main__':
    unittest.main() 