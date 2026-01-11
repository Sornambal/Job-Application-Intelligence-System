import base64
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
import os

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

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


def read_latest_emails(max_results=5):
    service = get_gmail_service()
    query = 'subject:(application OR applied OR interview OR shortlisted OR "thank you for applying" OR offer OR rejection OR rejected)'
    results = service.users().messages().list(
        userId='me',
        q=query,
        maxResults=max_results).execute()

    messages = results.get('messages', [])
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

    return emails
