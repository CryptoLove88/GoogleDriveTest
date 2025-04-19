# Google Drive File Manager

A Flask-based web application that provides a user-friendly interface for managing files in Google Drive. The application allows users to upload, download, delete, and navigate through their Google Drive files and folders.

## Features

- OAuth2 authentication with Google
- File upload and download
- File and folder deletion
- Folder navigation
- Modern and responsive UI
- Error handling and user feedback
- Comprehensive test coverage

## Prerequisites

- Python 3.8 or higher
- Google Cloud Platform account with Google Drive API enabled
- OAuth2 credentials (Client ID and Client Secret)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd google-drive-file-manager
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Project Structure

```
google-drive-file-manager/
├── app.py                  # Main application file
├── config/
│   └── config.py          # Configuration management
├── services/
│   ├── google_auth.py     # Google OAuth2 authentication
│   └── google_drive_service.py  # Google Drive operations
├── templates/
│   ├── dashboard.html     # Main dashboard template
│   └── login.html         # Login page template
├── tests/
│   ├── test_google_drive_service.py  # Unit tests
│   └── test_integration.py           # Integration tests
├── requirements.txt       # Project dependencies
└── README.md             # Project documentation
```

## Running the Application

1. Start the Flask development server:
```bash
python app.py
```

2. Open your web browser and navigate to `http://localhost:5000`

## Testing

The application includes both unit tests and integration tests. To run the tests:

```bash
# Run all tests
python -m unittest discover tests

# Run all tests with verbose output
python -m unittest discover tests -v

# Run specific test file
python -m unittest tests/test_google_drive_service.py
python -m unittest tests/test_integration.py

# Run specific test class
python -m unittest tests.test_google_drive_service.TestGoogleDriveFileOperation
python -m unittest tests.test_integration.TestIntegration
```

### Test Structure

- **Unit Tests**: Test individual components in isolation
  - `TestGoogleDriveFileOperation`: Tests file operations (upload, download, delete)
  - `TestGoogleDriveFolderOperation`: Tests folder operations (get name, get path)
  - `TestGoogleDriveFileMetadata`: Tests file metadata operations (get name, get parent)
  - `TestGoogleDriveService`: Tests the main service class

- **Integration Tests**: Test the application as a whole
  - `TestIntegration`: Tests the Flask routes and their interaction with the Google Drive service

## Code Documentation

### Configuration (`config/config.py`)

The configuration module manages application settings and environment variables. It includes:
- Base configuration class with default settings
- Environment-specific configurations (Development, Testing, Production)
- Environment variable loading and validation

### Google Drive Service (`services/google_drive_service.py`)

The Google Drive service handles all interactions with the Google Drive API:
- File operations (upload, download, delete)
- Folder operations (list, create, navigate)
- File metadata retrieval
- Error handling and logging

### Authentication (`services/google_auth.py`)

The authentication service manages OAuth2 flow:
- Authorization URL generation
- Token handling
- Credential management
- Session management

## Error Handling

The application implements comprehensive error handling:
- OAuth2 authentication errors
- File operation errors
- API rate limiting
- Network connectivity issues
- User feedback and error messages

## Security Considerations

- OAuth2 tokens are stored securely in the session
- CSRF protection enabled
- Secure session configuration
- Environment variables for sensitive data
- Input validation and sanitization

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Google Drive API Documentation
- Flask Documentation
- Python unittest Documentation 