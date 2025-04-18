import os
import pickle
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from datetime import datetime
import io

# Allow HTTP traffic for local development
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SESSION_TYPE'] = 'filesystem'

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/drive.file',
          'https://www.googleapis.com/auth/drive.metadata.readonly']

def get_google_drive_service():
    creds = None
    if 'token' in session:
        creds = Credentials.from_authorized_user_info(session['token'], SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = Flow.from_client_secrets_file(
                'credentials.json', SCOPES)
            flow.redirect_uri = url_for('oauth2callback', _external=True)
            authorization_url, state = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true')
            session['state'] = state
            return redirect(authorization_url)
        
        session['token'] = {
            'token': creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri': creds.token_uri,
            'client_id': creds.client_id,
            'client_secret': creds.client_secret,
            'scopes': creds.scopes
        }
    
    return build('drive', 'v3', credentials=creds)

@app.route('/')
def index():
    if 'token' not in session:
        return render_template('login.html')
    return redirect(url_for('dashboard'))

@app.route('/login')
def login():
    flow = Flow.from_client_secrets_file(
        'credentials.json', SCOPES)
    flow.redirect_uri = url_for('oauth2callback', _external=True)
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true')
    session['state'] = state
    return redirect(authorization_url)

@app.route('/oauth2callback')
def oauth2callback():
    state = session['state']
    flow = Flow.from_client_secrets_file(
        'credentials.json', SCOPES, state=state)
    flow.redirect_uri = url_for('oauth2callback', _external=True)
    
    authorization_response = request.url
    flow.fetch_token(authorization_response=authorization_response)
    credentials = flow.credentials
    
    session['token'] = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }
    
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'token' not in session:
        return redirect(url_for('login'))
    
    service = get_google_drive_service()
    results = service.files().list(
        pageSize=10,
        fields="nextPageToken, files(id, name, mimeType, modifiedTime)"
    ).execute()
    
    files = results.get('files', [])
    file_list = []
    
    for file in files:
        modified_time = datetime.fromisoformat(file['modifiedTime'].replace('Z', '+00:00'))
        file_info = {
            'id': file['id'],
            'name': file['name'],
            'type': file['mimeType'],
            'modified': modified_time.strftime('%Y-%m-%d %H:%M:%S')
        }
        file_list.append(file_info)
    
    return render_template('dashboard.html', files=file_list)

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
    
    # Save the file temporarily
    temp_path = os.path.join('temp', file.filename)
    os.makedirs('temp', exist_ok=True)
    file.save(temp_path)
    
    service = get_google_drive_service()
    file_metadata = {'name': file.filename}
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
    
    return redirect(url_for('dashboard'))

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