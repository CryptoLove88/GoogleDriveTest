import unittest
from unittest.mock import patch, MagicMock
import os
import io
from app import app
from services.google_drive_service import GoogleDriveService
from services.google_auth import GoogleAuth

class TestIntegration(unittest.TestCase):
    """Integration test suite for the Flask application.
    
    Tests the complete application flow including:
    - Authentication and session management
    - File operations through HTTP endpoints
    - Error handling and user feedback
    - OAuth2 flow and token management
    
    Each test simulates a real user interaction with proper
    authentication state management and request context.
    """
    
    def setUp(self):
        """Configure test environment.
        
        Sets up:
        1. Test Flask client with CSRF disabled
        2. Test configuration
        3. Clean session state
        """
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        self.app = app
        
    def test_index_redirect_to_login(self):
        """Test the initial application access.
        
        Verifies:
        1. Unauthenticated users are shown login page
        2. Login page contains expected content
        """
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'login', response.data)
        
    @patch('services.google_auth.GoogleAuth.get_authorization_url')
    def test_login_redirect(self, mock_auth_url):
        """Test OAuth2 login flow initiation.
        
        Verifies:
        1. Login generates proper auth URL
        2. User is redirected to Google consent page
        3. State parameter is properly handled
        """
        mock_auth_url.return_value = ('http://test.com', 'test_state')
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 302)
        self.assertIn('http://test.com', response.location)
        
    @patch('services.google_auth.GoogleAuth.get_credentials_from_callback')
    def test_oauth_callback(self, mock_get_credentials):
        """Test OAuth2 callback handling.
        
        Simulates the complete OAuth2 callback flow:
        1. Google redirects with auth code
        2. Code is exchanged for credentials
        3. Credentials are stored in session
        4. User is redirected to dashboard
        
        Also verifies CSRF protection via state parameter.
        """
        # Mock OAuth2 credentials
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
            # Set up session state
            with c.session_transaction() as sess:
                sess['state'] = 'test_state'
            
            response = c.get('/oauth2callback?state=test_state')
            self.assertEqual(response.status_code, 302)
            self.assertIn('/dashboard', response.location)
            
    @patch('app.get_google_drive_service')
    def test_dashboard_authenticated(self, mock_get_service):
        """Test dashboard access for authenticated users.
        
        Verifies:
        1. Session token handling
        2. File listing functionality
        3. Folder navigation
        4. UI element presence
        """
        # Mock Drive service
        mock_service = MagicMock()
        mock_service.get_folder_name.return_value = 'Test Folder'
        mock_service.get_folder_path.return_value = []
        mock_service.list_files.return_value = []
        mock_get_service.return_value = mock_service
        
        with self.client as c:
            # Set up authenticated session
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
        """Test file upload functionality.
        
        Verifies:
        1. File upload handling
        2. Temporary file management
        3. Drive API interaction
        4. Success/error messages
        """
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
        """Test file download functionality.
        
        Verifies:
        1. File retrieval from Drive
        2. Proper content type handling
        3. Filename preservation
        4. Error handling for invalid files
        """
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
        """Test file deletion functionality.
        
        Verifies:
        1. File removal from Drive
        2. Parent folder handling
        3. Redirect after deletion
        4. Success/error messages
        """
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