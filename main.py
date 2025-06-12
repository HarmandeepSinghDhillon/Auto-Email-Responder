from fastapi import FastAPI, BackgroundTasks
from googleapiclient.discovery import build
from auth import get_credentials
import base64
import re
import os

app = FastAPI()

@app.get("/auth")
def authenticate():
    if not os.path.exists("token.json"):
        from auth import get_credentials  # Import here to avoid circular imports
        creds = get_credentials()  # This should trigger the auth flow
        return {"status": "Authentication successful!"}
    return {"status": "Already authenticated"}

def get_unreplied_emails():
    creds = get_credentials()
    service = build('gmail', 'v1', credentials=creds)
    
    results = service.users().messages().list(userId='me', labelIds=['INBOX', 'UNREAD']).execute()
    messages = results.get('messages', [])
    
    unreplied_emails = []
    for msg in messages:
        email = service.users().messages().get(userId='me', id=msg['id']).execute()
        headers = email['payload']['headers']
        subject = next(h['value'] for h in headers if h['name'] == 'Subject')
        sender = next(h['value'] for h in headers if h['name'] == 'From')
        
        if re.search(r'support|help|question', subject, re.IGNORECASE):
            unreplied_emails.append({
                'id': msg['id'],
                'subject': subject,
                'sender': sender
            })
    return unreplied_emails

def send_auto_reply(email):
    creds = get_credentials()
    service = build('gmail', 'v1', credentials=creds)
    
    reply_message = f"""
    Hi there,
    Thank you for your email regarding "{email['subject']}".
    We have received your request and will get back to you within 24 hours.
    Best regards,
    Auto-Responder Bot
    """
    
    raw_message = f"To: {email['sender']}\nSubject: Re: {email['subject']}\n\n{reply_message}"
    encoded_message = base64.urlsafe_b64encode(raw_message.encode('utf-8')).decode('utf-8')
    
    service.users().messages().send(
        userId='me',
        body={'raw': encoded_message}
    ).execute()
    print(f"Replied to: {email['sender']}")

def process_emails():
    unreplied_emails = get_unreplied_emails()
    for email in unreplied_emails:
        send_auto_reply(email)

@app.get("/")
def home():
    return {"status": "Auto-Email Responder is running!"}

@app.post("/trigger")
async def trigger_responder(background_tasks: BackgroundTasks):
    background_tasks.add_task(process_emails)
    return {"status": "Processing emails in the background."}