import unittest
from unittest.mock import patch, MagicMock
import os
import io
from app import app
from services.google_drive_service import GoogleDriveService
from services.google_auth import GoogleAuth

class TestIntegration(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        self.app = app
        
    def test_index_redirect_to_login(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'login', response.data)
        
    @patch('services.google_auth.GoogleAuth.get_authorization_url')
    def test_login_redirect(self, mock_auth_url):
        mock_auth_url.return_value = ('http://test.com', 'test_state')
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 302)
        self.assertIn('http://test.com', response.location)
        
    @patch('services.google_auth.GoogleAuth.get_credentials_from_callback')
    def test_oauth_callback(self, mock_get_credentials):
        # Mock the credentials
        mock_credentials = MagicMock()
        mock_credentials.token = 'test_token'
        mock_credentials.refresh_token = 'test_refresh_token'
        mock_credentials.token_uri = 'test_uri'
        mock_credentials.client_id = 'test_client_id'
        mock_credentials.client_secret = 'test_client_secret'
        mock_credentials.scopes = ['test_scope']
        mock_credentials.expiry = None
        mock_get_credentials.return_value = mock_credentials
        
        with self.client as c:
            with c.session_transaction() as sess:
                sess['state'] = 'test_state'
            
            response = c.get('/oauth2callback?state=test_state')
            self.assertEqual(response.status_code, 302)
            self.assertIn('/dashboard', response.location)
            
    @patch('app.get_google_drive_service')
    def test_dashboard_authenticated(self, mock_get_service):
        # Mock the Google Drive service
        mock_service = MagicMock()
        mock_service.get_folder_name.return_value = 'Test Folder'
        mock_service.get_folder_path.return_value = []
        mock_service.list_files.return_value = []
        mock_get_service.return_value = mock_service
        
        with self.client as c:
            with c.session_transaction() as sess:
                sess['token'] = {
                    'token': 'test_token',
                    'refresh_token': 'test_refresh_token',
                    'token_uri': 'test_uri',
                    'client_id': 'test_client_id',
                    'client_secret': 'test_client_secret',
                    'scopes': ['test_scope'],
                    'expiry': None
                }
            
            response = c.get('/dashboard')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Test Folder', response.data)
            
    @patch('app.get_google_drive_service')
    def test_upload_file(self, mock_get_service):
        # Mock the Google Drive service
        mock_service = MagicMock()
        mock_service.upload_file.return_value = 'test_file_id'
        mock_get_service.return_value = mock_service
        
        # Create a test file
        test_file = io.BytesIO(b'test content')
        
        with self.client as c:
            with c.session_transaction() as sess:
                sess['token'] = {
                    'token': 'test_token',
                    'refresh_token': 'test_refresh_token',
                    'token_uri': 'test_uri',
                    'client_id': 'test_client_id',
                    'client_secret': 'test_client_secret',
                    'scopes': ['test_scope'],
                    'expiry': None
                }
            
            response = c.post(
                '/upload',
                data={
                    'file': (test_file, 'test.txt'),
                    'folder_id': 'root'
                },
                content_type='multipart/form-data'
            )
            self.assertEqual(response.status_code, 302)
            self.assertIn('/dashboard', response.location)
            
    @patch('app.get_google_drive_service')
    def test_download_file(self, mock_get_service):
        # Mock the Google Drive service
        mock_service = MagicMock()
        mock_service.download_file.return_value = io.BytesIO(b'test content')
        mock_service.get_file_name.return_value = 'test.txt'
        mock_get_service.return_value = mock_service
        
        with self.client as c:
            with c.session_transaction() as sess:
                sess['token'] = {
                    'token': 'test_token',
                    'refresh_token': 'test_refresh_token',
                    'token_uri': 'test_uri',
                    'client_id': 'test_client_id',
                    'client_secret': 'test_client_secret',
                    'scopes': ['test_scope'],
                    'expiry': None
                }
            
            response = c.get('/download/test_file_id')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data, b'test content')
            
    @patch('app.get_google_drive_service')
    def test_delete_file(self, mock_get_service):
        # Mock the Google Drive service
        mock_service = MagicMock()
        mock_service.get_file_parent.return_value = 'root'
        mock_get_service.return_value = mock_service
        
        with self.client as c:
            with c.session_transaction() as sess:
                sess['token'] = {
                    'token': 'test_token',
                    'refresh_token': 'test_refresh_token',
                    'token_uri': 'test_uri',
                    'client_id': 'test_client_id',
                    'client_secret': 'test_client_secret',
                    'scopes': ['test_scope'],
                    'expiry': None
                }
            
            response = c.get('/delete/test_file_id')
            self.assertEqual(response.status_code, 302)
            self.assertIn('/dashboard', response.location)

if __name__ == '__main__':
    unittest.main() 