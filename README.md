# Google Drive Manager

A Flask web application that allows users to manage their Google Drive files through a simple web interface.

## Features

- Google OAuth2 authentication
- View files in Google Drive
- Upload files to Google Drive
- Download files from Google Drive
- Delete files from Google Drive

## Prerequisites

- Python 3.9 or higher
- Google Cloud Platform account with Google Drive API enabled
- OAuth 2.0 credentials (client ID and client secret)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/google-drive-manager.git
cd google-drive-manager
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the required packages:
```bash
pip install -r requirements.txt
```

4. Set up Google OAuth credentials:
   - Go to the Google Cloud Console
   - Create a new project or select an existing one
   - Enable the Google Drive API
   - Create OAuth 2.0 credentials
   - Download the credentials and save them as `credentials.json` in the project root

## Usage

1. Start the Flask application:
```bash
python app.py
```

2. Open your web browser and navigate to `http://localhost:5000`
3. Sign in with your Google account
4. Start managing your Google Drive files

## Security Notes

- This application is for development purposes only
- Do not use the development server in production
- Keep your credentials secure and never commit them to version control
- Use environment variables for sensitive information in production

## License

This project is licensed under the MIT License - see the LICENSE file for details. 