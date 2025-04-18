import os
import json
from dotenv import load_dotenv

class Config:
    """Base configuration class."""
    
    # Flask settings
    SECRET_KEY = os.getenv('SECRET_KEY', os.urandom(24))
    SESSION_TYPE = 'filesystem'
    
    # Google Drive API scopes
    GOOGLE_DRIVE_SCOPES = [
        'https://www.googleapis.com/auth/drive',
        'https://www.googleapis.com/auth/drive.metadata.readonly',
        'https://www.googleapis.com/auth/drive.file'
    ]
    
    # File upload settings
    UPLOAD_FOLDER = 'temp'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    @classmethod
    def load_credentials(cls):
        """Load OAuth credentials from credentials.json file."""
        try:
            with open('credentials.json', 'r') as f:
                credentials = json.load(f)
                cls.GOOGLE_CLIENT_ID = credentials['web']['client_id']
                cls.GOOGLE_CLIENT_SECRET = credentials['web']['client_secret']
                cls.GOOGLE_REDIRECT_URI = credentials['web']['redirect_uris'][0]
        except Exception as e:
            print(f"Error loading credentials: {str(e)}")
            raise
    
    @classmethod
    def validate(cls):
        """Validate that all required configuration values are set."""
        required_vars = [
            'GOOGLE_CLIENT_ID',
            'GOOGLE_CLIENT_SECRET',
            'GOOGLE_REDIRECT_URI'
        ]
        
        missing_vars = [var for var in required_vars if not hasattr(cls, var)]
        
        if missing_vars:
            raise ValueError(f"Missing required configuration values: {', '.join(missing_vars)}")

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    OAUTHLIB_INSECURE_TRANSPORT = '1'  # Allow HTTP traffic for local development

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    OAUTHLIB_INSECURE_TRANSPORT = '1'

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    OAUTHLIB_INSECURE_TRANSPORT = '0'  # Disallow HTTP traffic in production

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

# Load credentials
Config.load_credentials() 