from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

class GoogleAuth:
    """Class to handle Google OAuth2.0 authorization.
    
    This class manages the complete OAuth2.0 flow for Google Drive API access:
    1. Generates authorization URLs for user consent
    2. Handles OAuth callbacks and token generation
    3. Manages token refresh and persistence
    4. Creates authenticated Google Drive API service instances
    """
    
    def __init__(self, config):
        """Initialize with configuration settings.
        
        Sets up the OAuth2 configuration using the provided config object.
        The scopes determine what level of access the application has to the user's Google Drive.
        
        Args:
            config: Configuration object containing Google OAuth2 credentials and settings
        """
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
        """Create and return an OAuth2 flow instance.
        
        Creates a Flow object that handles the OAuth2 authorization process.
        The state parameter helps prevent CSRF attacks by ensuring the callback
        matches the original authorization request.
        
        Args:
            state: Optional state string for CSRF protection
            
        Returns:
            Flow: Configured OAuth2 flow instance
        """
        flow = Flow.from_client_config(
            self.client_config,
            scopes=self.scopes,
            state=state
        )
        return flow
    
    def get_authorization_url(self):
        """Get the authorization URL for OAuth2 flow.
        
        Generates a URL where users can consent to the application's access request.
        Uses offline access to enable token refresh and includes all granted scopes.
        
        Returns:
            tuple: (authorization_url: str, state: str)
                - authorization_url: URL where user should be redirected for consent
                - state: Random state string for CSRF protection
        """
        flow = self.get_oauth_flow()
        flow.redirect_uri = self.config.GOOGLE_REDIRECT_URI
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        return authorization_url, state
    
    def get_credentials_from_callback(self, authorization_response, state=None):
        """Get credentials from OAuth2 callback.
        
        Exchanges the authorization code from the callback for access credentials.
        Verifies the state parameter to prevent CSRF attacks.
        
        Args:
            authorization_response: Full callback URL with authorization code
            state: State string from the original authorization request
            
        Returns:
            Credentials: Google OAuth2 credentials object
            
        Raises:
            ValueError: If state verification fails
        """
        flow = self.get_oauth_flow(state=state)
        flow.redirect_uri = self.config.GOOGLE_REDIRECT_URI
        flow.fetch_token(authorization_response=authorization_response)
        return flow.credentials
    
    def create_credentials_from_token(self, token_info):
        """Create credentials from token information.
        
        Reconstructs a Credentials object from previously stored token data.
        This is used when resuming a session with stored credentials.
        
        Args:
            token_info: Dict containing token data (token, refresh_token, etc.)
            
        Returns:
            Credentials: Reconstructed Google OAuth2 credentials object
        """
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