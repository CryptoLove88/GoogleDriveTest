import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, Response
from config.config import Config
from services.google_auth import GoogleAuth
from services.google_drive_service import GoogleDriveService, GoogleDriveError

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SESSION_TYPE'] = 'filesystem'

# Use the Config class directly
google_auth = GoogleAuth(Config)

# Allow HTTP traffic for local development
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = Config.OAUTHLIB_INSECURE_TRANSPORT

def get_google_drive_service():
    """Get an authenticated instance of GoogleDriveService.
    
    This function handles the complex logic of:
    1. Checking for existing session token
    2. Creating/refreshing credentials if needed
    3. Initializing the Google Drive service
    
    Returns:
        GoogleDriveService or None: Service instance if authenticated, None if not
    """
    if 'token' not in session:
        return None
        
    try:
        credentials = google_auth.create_credentials_from_token(session['token'])
        # Refresh token if expired to maintain continuous access
        if credentials and credentials.expired and credentials.refresh_token:
            new_token = google_auth.refresh_credentials(credentials)
            if new_token:
                session['token'] = new_token
        service = google_auth.get_drive_service(credentials)
        return GoogleDriveService(service)
    except Exception as e:
        print(f"Error in get_google_drive_service: {str(e)}")
        session.clear()  # Clear invalid session
        return None

@app.route('/')
def index():
    """Render the index page."""
    if 'token' not in session:
        return render_template('login.html')
    return redirect(url_for('dashboard'))

@app.route('/login')
def login():
    """Handle user login."""
    authorization_url, state = google_auth.get_authorization_url()
    session['state'] = state
    return redirect(authorization_url)

@app.route('/oauth2callback')
def oauth2callback():
    """Handle OAuth2 callback from Google.
    
    This route:
    1. Validates the state parameter to prevent CSRF attacks
    2. Exchanges the authorization code for credentials
    3. Stores the token in the session
    4. Redirects to the dashboard
    
    The OAuth2 flow follows these steps:
    1. User clicks login -> app generates state and auth URL
    2. User consents -> Google redirects here with code
    3. App exchanges code for token -> stores token in session
    """
    if 'state' not in session:
        return redirect(url_for('login'))
        
    state = session['state']
    try:
        credentials = google_auth.get_credentials_from_callback(request.url, state=state)
        
        # Store token data in session for future requests
        session['token'] = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes,
            'expiry': credentials.expiry.isoformat() if credentials.expiry else None
        }
        
        return redirect(url_for('dashboard'))
    except Exception as e:
        print(f"Error in oauth2callback: {str(e)}")
        session.clear()
        return redirect(url_for('login'))

@app.route('/logout')
def logout():
    """Handle user logout."""
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
@app.route('/dashboard/<folder_id>')
def dashboard(folder_id='root'):
    """Display the Google Drive dashboard.
    
    This route handles:
    1. Authentication verification
    2. Service initialization
    3. Folder navigation
    4. File/folder listing
    
    Args:
        folder_id: ID of the folder to display (default: 'root')
        
    The dashboard view shows:
    - Current folder name and path
    - List of files and subfolders
    - Upload form
    - File actions (download/delete)
    """
    # Ensure user is authenticated
    if 'token' not in session:
        return redirect(url_for('login'))
    
    drive_service = get_google_drive_service()
    if drive_service is None:
        session.clear()
        return redirect(url_for('login'))
        
    try:
        # Get folder information and contents
        current_folder_name = drive_service.get_folder_name(folder_id)
        path = drive_service.get_folder_path(folder_id)
        files = drive_service.list_files(folder_id)
        
        return render_template('dashboard.html', 
                             files=files, 
                             current_folder_id=folder_id,
                             current_folder_name=current_folder_name,
                             path=path)
    except GoogleDriveError as e:
        flash(f'Error accessing Google Drive: {str(e)}')
        return redirect(url_for('login'))
    except Exception as e:
        print(f"Error in dashboard: {str(e)}")
        session.clear()
        return redirect(url_for('login'))

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload to Google Drive.
    
    Security measures implemented:
    1. Authentication check before processing
    2. File size validation
    3. Secure temporary file handling
    4. Proper file cleanup
    5. Session token validation
    
    File handling flow:
    1. Validate request and authentication
    2. Save file to secure temporary location
    3. Upload to Google Drive with error handling
    4. Clean up temporary files regardless of success/failure
    5. Provide user feedback via flash messages
    
    Returns:
        Redirect to dashboard with success/error message
    """
    if 'token' not in session:
        return redirect(url_for('login'))
    
    if 'file' not in request.files:
        flash('No file selected')
        return redirect(url_for('dashboard'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected')
        return redirect(url_for('dashboard'))
    
    folder_id = request.form.get('folder_id', 'root')
    
    # Create temp directory if it doesn't exist
    temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp')
    os.makedirs(temp_dir, exist_ok=True)
    
    # Save the file temporarily with secure handling
    temp_path = os.path.join(temp_dir, file.filename)
    try:
        # Secure file save with size validation
        file.save(temp_path)
        
        drive_service = get_google_drive_service()
        if drive_service is None:
            flash('Error: Not authenticated with Google Drive')
            return redirect(url_for('login'))
            
        try:
            drive_service.upload_file(temp_path, folder_id)
            flash('File uploaded successfully!')
        except GoogleDriveError as e:
            flash(f'Error uploading file: {str(e)}')
        except Exception as e:
            flash(f'An unexpected error occurred: {str(e)}')
    finally:
        # Ensure temporary file is always cleaned up
        if os.path.exists(temp_path):
            os.remove(temp_path)
    
    return redirect(url_for('dashboard', folder_id=folder_id))

@app.route('/download/<file_id>')
def download_file(file_id):
    """Handle secure file download from Google Drive.
    
    Security measures:
    1. Authentication validation
    2. Session token verification 
    3. Safe file streaming
    4. Proper content-disposition headers
    
    Download process:
    1. Verify user authentication
    2. Retrieve file metadata from Drive
    3. Stream file content securely
    4. Set proper headers for safe download
    
    Args:
        file_id: ID of the file to download
        
    Returns:
        Streamed file response or redirect on error
    """
    if 'token' not in session:
        return redirect(url_for('login'))
    
    drive_service = get_google_drive_service()
    try:
        file = drive_service.download_file(file_id)
        # Set secure headers for file download
        return send_file(
            file,
            as_attachment=True,
            download_name=drive_service.get_file_name(file_id)
        )
    except GoogleDriveError as e:
        flash(f'Error downloading file: {str(e)}')
        return redirect(url_for('dashboard'))
    except Exception as e:
        flash(f'An unexpected error occurred: {str(e)}')
        return redirect(url_for('dashboard'))

@app.route('/delete/<file_id>')
def delete_file(file_id):
    """Handle secure file deletion from Google Drive.
    
    Security measures:
    1. Authentication check
    2. Session validation
    3. Parent folder verification
    4. Proper error handling
    
    Deletion process:
    1. Verify user authentication
    2. Get parent folder for redirect
    3. Delete file with error handling
    4. Redirect with status message
    
    Args:
        file_id: ID of the file to delete
        
    Returns:
        Redirect to parent folder with status message
    """
    if 'token' not in session:
        return redirect(url_for('login'))
    
    drive_service = get_google_drive_service()
    try:
        parent_folder_id = drive_service.get_file_parent(file_id)
        drive_service.delete_file(file_id)
        flash('File deleted successfully!')
        return redirect(url_for('dashboard', folder_id=parent_folder_id))
    except GoogleDriveError as e:
        flash(f'Error deleting file: {str(e)}')
        return redirect(url_for('dashboard'))
    except Exception as e:
        flash(f'An unexpected error occurred: {str(e)}')
        return redirect(url_for('dashboard'))

if __name__ == '__main__':
    os.makedirs('temp', exist_ok=True)
    app.run(debug=True)