from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

class GoogleAuth:
    """Class to handle Google OAuth2.0 authorization."""
    
    def __init__(self, config):
        """Initialize with configuration settings."""
        self.config = config
        self.scopes = config.GOOGLE_DRIVE_SCOPES
        self.client_config = {
            "web": {
                "client_id": config.GOOGLE_CLIENT_ID,
                "client_secret": config.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uri": config.GOOGLE_REDIRECT_URI,
            }
        }
    
    def get_oauth_flow(self, state=None):
        """Create and return an OAuth2 flow instance."""
        flow = Flow.from_client_config(
            self.client_config,
            scopes=self.scopes,
            state=state
        )
        return flow
    
    def get_authorization_url(self):
        """Get the authorization URL for OAuth2 flow."""
        flow = self.get_oauth_flow()
        flow.redirect_uri = self.config.GOOGLE_REDIRECT_URI
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        return authorization_url, state
    
    def get_credentials_from_callback(self, authorization_response, state=None):
        """Get credentials from OAuth2 callback."""
        flow = self.get_oauth_flow(state=state)
        flow.redirect_uri = self.config.GOOGLE_REDIRECT_URI
        flow.fetch_token(authorization_response=authorization_response)
        return flow.credentials
    
    def create_credentials_from_token(self, token_info):
        """Create credentials from token information."""
        return Credentials.from_authorized_user_info(token_info, self.scopes)
    
    def refresh_credentials(self, credentials):
        """Refresh expired credentials."""
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
            return {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes,
                'expiry': credentials.expiry.isoformat() if credentials.expiry else None
            }
        return None
    
    def get_drive_service(self, credentials):
        """Build and return the Google Drive service."""
        return build('drive', 'v3', credentials=credentials) 