from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle
import os
from datetime import datetime, timezone
import pytz

SCOPES = ['https://www.googleapis.com/auth/calendar']
CALENDAR_ID = 'cohere@unforced.org'

def get_calendar_service():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    
    return build('calendar', 'v3', credentials=creds)

def format_time(dt_str):
    dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    mountain = pytz.timezone('America/Denver')
    dt_mountain = dt.astimezone(mountain)
    return dt_mountain.strftime("%-I:%M%p").lower()

def format_date(dt_str):
    dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    mountain = pytz.timezone('America/Denver')
    dt_mountain = dt.astimezone(mountain)
    return dt_mountain.strftime("%-m/%-d")

def main():
    service = get_calendar_service()
    
    # Get current time in UTC ISO format
    now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    
    # Get events from the calendar
    events_result = service.events().list(
        calendarId=CALENDAR_ID,
        timeMin=now,
        maxResults=100,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    
    events = events_result.get('items', [])
    
    if not events:
        print('No upcoming events found.')
        return
    
    # Create markdown content
    markdown_content = "# Upcoming Events\n\n"
    
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        end = event['end'].get('dateTime', event['end'].get('date'))
        location = event.get('location', 'No location specified')
        title = event['summary']
        description = event.get('description', '')
        html_link = event.get('htmlLink', '')
        
        # Format the event line
        event_line = f"* {format_date(start)} {format_time(start)}-{format_time(end)} at {location} - [{title}]({html_link})\n"
        markdown_content += event_line
    
    # Write to file
    with open('events.md', 'w') as f:
        f.write(markdown_content)
    
    print("Events have been written to events.md")

if __name__ == '__main__':
    main()
