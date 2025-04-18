import os
import pickle
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, Response
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from datetime import datetime
import io
from config.config import config
from services.google_auth import GoogleAuth
from services.google_drive import GoogleDrive

# Allow HTTP traffic for local development
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SESSION_TYPE'] = 'filesystem'

# Get the appropriate config class based on environment
config_class = config['development']  # or 'production' or 'testing'
google_auth = GoogleAuth(config_class)

def get_google_drive():
    if 'token' not in session:
        return None
        
    try:
        credentials = google_auth.create_credentials_from_token(session['token'])
        if credentials and credentials.expired and credentials.refresh_token:
            new_token = google_auth.refresh_credentials(credentials)
            if new_token:
                session['token'] = new_token
        service = google_auth.get_drive_service(credentials)
        return GoogleDrive(service)
    except Exception as e:
        print(f"Error in get_google_drive: {str(e)}")
        session.clear()
        return None

@app.route('/')
def index():
    if 'token' not in session:
        return render_template('login.html')
    return redirect(url_for('dashboard'))

@app.route('/login')
def login():
    # Use the redirect URI from the config
    authorization_url, state = google_auth.get_authorization_url()
    session['state'] = state
    return redirect(authorization_url)

@app.route('/oauth2callback')
def oauth2callback():
    if 'state' not in session:
        return redirect(url_for('login'))
        
    state = session['state']
    try:
        # Use the redirect URI from the config
        credentials = google_auth.get_credentials_from_callback(request.url, state=state)
        
        # Store token information in session
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
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
@app.route('/dashboard/<folder_id>')
def dashboard(folder_id='root'):
    if 'token' not in session:
        return redirect(url_for('login'))
    
    drive = get_google_drive()
    if drive is None:
        session.clear()
        return redirect(url_for('login'))
        
    try:
        # Get the current folder name
        current_folder_name = drive.get_folder_name(folder_id)
        
        # Get the path for breadcrumb navigation
        path = drive.get_folder_path(folder_id)
        
        # List files and folders
        files = drive.list_files(folder_id)
        
        return render_template('dashboard.html', 
                             files=files, 
                             current_folder_id=folder_id,
                             current_folder_name=current_folder_name,
                             path=path)
    except Exception as e:
        print(f"Error in dashboard: {str(e)}")
        session.clear()
        return redirect(url_for('login'))

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'token' not in session:
        return redirect(url_for('login'))
    
    if 'file' not in request.files:
        flash('No file selected')
        return redirect(url_for('dashboard'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected')
        return redirect(url_for('dashboard'))
    
    # Get the folder ID from the form, default to 'root' if not provided
    folder_id = request.form.get('folder_id', 'root')
    
    # Save the file temporarily
    temp_path = os.path.join('temp', file.filename)
    os.makedirs('temp', exist_ok=True)
    file.save(temp_path)
    
    drive = get_google_drive()
    try:
        drive.upload_file(temp_path, folder_id)
        flash('File uploaded successfully!')
    except Exception as e:
        flash(f'An error occurred: {str(e)}')
    finally:
        # Clean up the temporary file
        os.remove(temp_path)
    
    # Redirect back to the current folder
    return redirect(url_for('dashboard', folder_id=folder_id))

@app.route('/download/<file_id>')
def download_file(file_id):
    if 'token' not in session:
        return redirect(url_for('login'))
    
    drive = get_google_drive()
    try:
        file = drive.download_file(file_id)
        return send_file(
            file,
            as_attachment=True,
            download_name=drive.get_file_name(file_id)
        )
    except Exception as e:
        flash(f'An error occurred: {str(e)}')
        return redirect(url_for('dashboard'))

@app.route('/delete/<file_id>')
def delete_file(file_id):
    if 'token' not in session:
        return redirect(url_for('login'))
    
    drive = get_google_drive()
    try:
        # Get the parent folder ID before deleting the file
        file_metadata = drive.service.files().get(
            fileId=file_id,
            fields="parents"
        ).execute()
        parent_folder_id = file_metadata.get('parents', ['root'])[0]
        
        # Delete the file
        drive.delete_file(file_id)
        flash('File deleted successfully!')
        
        # Redirect back to the parent folder
        return redirect(url_for('dashboard', folder_id=parent_folder_id))
    except Exception as e:
        flash(f'An error occurred: {str(e)}')
        return redirect(url_for('dashboard'))

if __name__ == '__main__':
    os.makedirs('temp', exist_ok=True)
    app.run(debug=True) 