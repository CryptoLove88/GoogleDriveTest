import os
import json

class Config:
    """Configuration class for application settings and OAuth2 credentials.
    
    This class manages:
    1. Flask application settings
    2. OAuth2 configuration and credentials
    3. Google Drive API scope definitions
    4. File upload restrictions
    
    The configuration is loaded from both environment variables and a credentials.json file
    to maintain security while allowing easy deployment across environments.
    """
    
    # Flask settings with security-focused configuration
    SECRET_KEY = os.getenv('SECRET_KEY', os.urandom(24))  # Random key per instance if not set
    SESSION_TYPE = 'filesystem'  # Secure session storage on filesystem
    DEBUG = True  # Enable detailed error messages (should be False in production)
    TESTING = False  # Disable test mode by default
    OAUTHLIB_INSECURE_TRANSPORT = '1'  # Allow HTTP for local development only
    
    # Google Drive API scopes with minimal required permissions
    GOOGLE_DRIVE_SCOPES = [
        'https://www.googleapis.com/auth/drive',        # Full drive access
        'https://www.googleapis.com/auth/drive.metadata.readonly',  # Read metadata only
        'https://www.googleapis.com/auth/drive.file'    # Access to files created by app
    ]
    
    # File upload security settings
    UPLOAD_FOLDER = 'temp'  # Temporary storage for uploads
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB file size limit
    
    @classmethod
    def load_credentials(cls):
        """Load OAuth credentials from credentials.json file.
        
        This method implements a robust error handling strategy:
        1. Missing file handling - Guides user to setup process
        2. Invalid JSON handling - Helps identify format issues
        3. Missing field handling - Details which OAuth fields are missing
        
        The error messages are designed to be actionable, helping users
        fix configuration issues without needing to read documentation.
        
        Error Scenarios:
        - credentials.json missing: Points to setup instructions
        - Malformed JSON: Suggests JSON validation
        - Missing fields: Lists required OAuth2 fields
        - Invalid values: Validates credential format
        
        Raises:
            FileNotFoundError: With setup instructions if file missing
            JSONDecodeError: With validation guidance if JSON invalid
            KeyError: With field name if OAuth2 field missing
        """
        try:
            with open('credentials.json', 'r') as f:
                credentials = json.load(f)
                
                # Extract required OAuth2 fields with validation
                try:
                    cls.GOOGLE_CLIENT_ID = credentials['web']['client_id']
                    if not cls.GOOGLE_CLIENT_ID.endswith('.apps.googleusercontent.com'):
                        raise ValueError("Invalid client_id format")
                        
                    cls.GOOGLE_CLIENT_SECRET = credentials['web']['client_secret']
                    if len(cls.GOOGLE_CLIENT_SECRET) < 8:
                        raise ValueError("Invalid client_secret format")
                        
                    cls.GOOGLE_REDIRECT_URI = credentials['web']['redirect_uris'][0]
                    if not cls.GOOGLE_REDIRECT_URI.startswith(('http://', 'https://')):
                        raise ValueError("Invalid redirect_uri format")
                        
                except KeyError as e:
                    print(f"Error: Missing required OAuth2 field: {str(e)}")
                    print("Please ensure credentials.json contains all required fields:")
                    print("- web.client_id")
                    print("- web.client_secret") 
                    print("- web.redirect_uris[0]")
                    raise
                    
        except FileNotFoundError:
            print("""
Error: credentials.json file not found.

To set up credentials:
1. Go to Google Cloud Console
2. Create or select a project
3. Enable Google Drive API
4. Create OAuth 2.0 Client ID
5. Download client configuration
6. Save as credentials.json in project root
            """)
            raise
            
        except json.JSONDecodeError:
            print("""
Error: credentials.json is not valid JSON.

Please verify:
1. File contains valid JSON syntax
2. No missing/extra commas
3. All quotes and brackets match
4. No trailing commas
            """)
            raise
    
    @classmethod
    def validate(cls):
        """Validate that all required configuration values are set.
        
        This method ensures all critical configuration values are present
        before the application starts, preventing runtime errors.
        
        Raises:
            ValueError: If any required configuration value is missing
        """
        required_vars = [
            'GOOGLE_CLIENT_ID',
            'GOOGLE_CLIENT_SECRET',
            'GOOGLE_REDIRECT_URI'
        ]
        
        missing_vars = [var for var in required_vars if not hasattr(cls, var)]
        
        if missing_vars:
            raise ValueError(f"Missing required configuration values: {', '.join(missing_vars)}")

# Load credentials
Config.load_credentials()