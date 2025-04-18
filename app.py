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

# Allow HTTP traffic for local development
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SESSION_TYPE'] = 'filesystem'

# Get the appropriate config class based on environment
config_class = config['development']  # or 'production' or 'testing'

# If modifying these scopes, delete the file token.pickle.
SCOPES = config_class.GOOGLE_DRIVE_SCOPES

def get_google_drive_service():
    if 'token' not in session:
        return None
        
    try:
        creds = Credentials.from_authorized_user_info(session['token'], SCOPES)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            session['token'] = {
                'token': creds.token,
                'refresh_token': creds.refresh_token,
                'token_uri': creds.token_uri,
                'client_id': creds.client_id,
                'client_secret': creds.client_secret,
                'scopes': creds.scopes
            }
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        print(f"Error in get_google_drive_service: {str(e)}")
        session.clear()
        return None

@app.route('/')
def index():
    if 'token' not in session:
        return render_template('login.html')
    return redirect(url_for('dashboard'))

@app.route('/login')
def login():
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": config_class.GOOGLE_CLIENT_ID,
                "client_secret": config_class.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uri": config_class.GOOGLE_REDIRECT_URI,
            }
        },
        scopes=SCOPES
    )
    flow.redirect_uri = url_for('oauth2callback', _external=True)
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true')
    session['state'] = state
    return redirect(authorization_url)

@app.route('/oauth2callback')
def oauth2callback():
    if 'state' not in session:
        return redirect(url_for('login'))
        
    state = session['state']
    try:
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": config_class.GOOGLE_CLIENT_ID,
                    "client_secret": config_class.GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uri": config_class.GOOGLE_REDIRECT_URI,
                }
            },
            scopes=SCOPES,
            state=state
        )
        flow.redirect_uri = url_for('oauth2callback', _external=True)
        
        authorization_response = request.url
        flow.fetch_token(authorization_response=authorization_response)
        credentials = flow.credentials
        
        # Store all required fields for token refresh
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
    
    service = get_google_drive_service()
    if service is None:
        session.clear()
        return redirect(url_for('login'))
        
    try:
        # Get the current folder name if not root
        current_folder_name = "Root"
        if folder_id != 'root':
            folder = service.files().get(
                fileId=folder_id,
                fields="name"
            ).execute()
            current_folder_name = folder.get('name', 'Unknown Folder')

        # Build the path for breadcrumb navigation
        path = []
        if folder_id != 'root':
            current_id = folder_id
            while current_id != 'root':
                try:
                    file = service.files().get(
                        fileId=current_id,
                        fields="id, name, parents"
                    ).execute()
                    
                    path.insert(0, {
                        'id': file['id'],
                        'name': file['name']
                    })
                    
                    # Get the parent folder ID
                    parents = file.get('parents', [])
                    if parents:
                        current_id = parents[0]
                    else:
                        break
                except Exception as e:
                    print(f"Error getting parent folder: {str(e)}")
                    break

        # List files and folders in the current directory
        query = f"'{folder_id}' in parents and trashed = false"
        results = service.files().list(
            q=query,
            pageSize=50,
            fields="nextPageToken, files(id, name, mimeType, modifiedTime)",
            orderBy="folder,name"
        ).execute()
        
        files = results.get('files', [])
        file_list = []
        
        for file in files:
            modified_time = datetime.fromisoformat(file['modifiedTime'].replace('Z', '+00:00'))
            is_folder = file['mimeType'] == 'application/vnd.google-apps.folder'
            
            file_info = {
                'id': file['id'],
                'name': file['name'],
                'type': file['mimeType'],
                'modified': modified_time.strftime('%Y-%m-%d %H:%M:%S'),
                'is_folder': is_folder
            }
            file_list.append(file_info)
        
        return render_template('dashboard.html', 
                             files=file_list, 
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
    
    service = get_google_drive_service()
    file_metadata = {
        'name': file.filename,
        'parents': [folder_id]  # Set the parent folder
    }
    media = MediaFileUpload(temp_path, resumable=True)
    
    try:
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
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
    
    service = get_google_drive_service()
    try:
        request = service.files().get_media(fileId=file_id)
        file = io.BytesIO()
        downloader = MediaIoBaseDownload(file, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        
        file.seek(0)
        return send_file(
            file,
            as_attachment=True,
            download_name=service.files().get(fileId=file_id).execute()['name']
        )
    except Exception as e:
        flash(f'An error occurred: {str(e)}')
        return redirect(url_for('dashboard'))

@app.route('/delete/<file_id>')
def delete_file(file_id):
    if 'token' not in session:
        return redirect(url_for('login'))
    
    service = get_google_drive_service()
    try:
        service.files().delete(fileId=file_id).execute()
        flash('File deleted successfully!')
    except Exception as e:
        flash(f'An error occurred: {str(e)}')
    
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    os.makedirs('temp', exist_ok=True)
    app.run(debug=True) 