import base64
import pickle
import os
import time
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
BASE_QUERY = 'subject:(application OR applied OR interview OR shortlisted OR "thank you for applying" OR offer OR rejection OR rejected)'
LAST_RUN_FILE = 'last_run.txt'


def _load_last_run_epoch():
    if not os.path.exists(LAST_RUN_FILE):
        return None
    try:
        with open(LAST_RUN_FILE, 'r', encoding='utf-8') as f:
            return int(float(f.read().strip()))
    except (ValueError, OSError):
        return None


def _save_last_run_epoch(epoch: float):
    try:
        with open(LAST_RUN_FILE, 'w', encoding='utf-8') as f:
            f.write(str(int(epoch)))
    except OSError:
        pass

def get_gmail_service():
    creds = None

    if os.path.exists('token.pkl'):
        try:
            with open('token.pkl', 'rb') as token:
                creds = pickle.load(token)
        except (EOFError, pickle.UnpicklingError):
            # Corrupt or empty token file; drop it and re-auth
            os.remove('token.pkl')
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        with open('token.pkl', 'wb') as token:
            pickle.dump(creds, token)

    service = build('gmail', 'v1', credentials=creds)
    return service


def read_latest_emails(max_results=50, since_last_run=True):
    service = get_gmail_service()

    # Build Gmail search query; add after:<epoch> to fetch only new mail since last run
    query = BASE_QUERY
    last_run_epoch = _load_last_run_epoch() if since_last_run else None
    if last_run_epoch:
        query = f"{query} after:{last_run_epoch}"

    messages = []
    page_token = None
    while True:
        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_results,
            pageToken=page_token
        ).execute()

        messages.extend(results.get('messages', []))
        page_token = results.get('nextPageToken')
        if not page_token:
            break

    emails = []
    for msg in messages:
        txt = service.users().messages().get(
            userId='me', id=msg['id'], format='full').execute()

        payload = txt['payload']
        headers = payload.get('headers', [])

        subject = sender = ""
        for h in headers:
            if h['name'] == 'Subject':
                subject = h['value']
            if h['name'] == 'From':
                sender = h['value']

        parts = payload.get('parts', [])
        body = ""

        for part in parts:
            if part['mimeType'] == 'text/plain':
                body = base64.urlsafe_b64decode(
                    part['body']['data']).decode('utf-8')

        emails.append({
            "subject": subject,
            "sender": sender,
            "body": body
        })

    if since_last_run:
        _save_last_run_epoch(time.time())

    return emails
