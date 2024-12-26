from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime, timezone
import aisuite as ai
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get environment variables
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

# Initialize Flask app
app = Flask(__name__, static_folder='static')
app.config['TESTING'] = True
CORS(app)

# Initialize calendar service if credentials exist
calendar_service = None
if os.path.exists('credentials.json'):
    calendar_service = get_calendar_service()

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/calendar']

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

def validate_event_details(event_details):
    """Validate the parsed event details and return any issues."""
    required_fields = ['title', 'description', 'start_time', 'end_time', 'location']
    issues = []
    
    try:
        event_dict = json.loads(event_details) if isinstance(event_details, str) else event_details
        logger.info(f"Validating event details: {event_dict}")
        
        # Check for missing fields
        for field in required_fields:
            if field not in event_dict:
                issues.append(f"Missing required field: {field}")
            elif not event_dict[field]:
                issues.append(f"Empty value for field: {field}")
        
        # Validate datetime formats if present
        if 'start_time' in event_dict and event_dict['start_time']:
            try:
                datetime.fromisoformat(event_dict['start_time'].replace('Z', '+00:00'))
            except ValueError as e:
                issues.append(f"Invalid start_time format: {str(e)}")
        
        if 'end_time' in event_dict and event_dict['end_time']:
            try:
                datetime.fromisoformat(event_dict['end_time'].replace('Z', '+00:00'))
            except ValueError as e:
                issues.append(f"Invalid end_time format: {str(e)}")
        
        return issues
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {str(e)}")
        return [f"Failed to parse AI response as JSON: {str(e)}"]
    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        return [f"Validation error: {str(e)}"]

def parse_event_with_ai(page_content, source_url, description_style="default"):
    client = ai.Client()
    
    description_prompts = {
        "default": "A comprehensive description that includes all relevant details about the event. Include any important information like agenda, speakers, requirements, or special notes.",
        "telegram": "A brief, concise summary of the event (2-3 sentences max) highlighting only the most important details. Focus on what, when, and why someone might want to attend."
    }
    
    description_prompt = description_prompts.get(description_style, description_prompts["default"])
    
    prompt = f"""Extract event details from the following webpage content. 
    Return a JSON object with these fields:
    - title: event title
    - description: {description_prompt} Start the description with 'Source: {source_url}\n\n' followed by the description.
    - start_time: start time in ISO format
    - end_time: end time in ISO format
    - location: event location

    Give just the json object with no extra text or formatting.

    Webpage content:
    {page_content}
    """
    
    messages = [{
        "role": "system",
        "content": "You are an AI assistant that helps users parse events from webpages. Always return valid JSON with the specified fields. Use ISO format for dates (YYYY-MM-DDTHH:MM:SS+HH:MM). For descriptions, be comprehensive and include all relevant details from the source, properly formatted for readability."
    }]
    
    messages.append({
        "role": "user",
        "content": prompt
    })
    
    try:
        response = client.chat.completions.create(
            messages=messages,
            model="anthropic:claude-3-5-sonnet-20240620",
            max_tokens=5000,
            temperature=0.5
        )
        
        logger.info(f"AI Response: {response.choices[0].message.content}")
        return response.choices[0].message.content
    except Exception as e:
        logger.error(e)
        logger.error(f"AI parsing error: {str(e)}")
        raise

@app.route('/')
def serve_frontend():
    return send_from_directory(app.static_folder, 'index.html')

# Serve static files
@app.route('/<path:path>')
def serve_static(path):
    if path.startswith('assets/'):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/parse-event', methods=['POST'])
def parse_event():
    url = request.json.get('url')
    description_style = request.json.get('description_style', 'default')
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    try:
        # Fetch webpage content
        logger.info(f"Fetching content from URL: {url}")
        response = requests.get(url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Get text content, preserving some structure
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
            
        # Get text with some basic formatting preserved
        lines = []
        for element in soup.find_all(['p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li']):
            text = element.get_text(strip=True)
            if text:  # Only add non-empty lines
                lines.append(text)
        
        text_content = "\n\n".join(lines)  # Join with double newlines for better separation
        
        # Use AI to parse the event details
        logger.info("Parsing event details with AI")
        event_details = parse_event_with_ai(text_content, url, description_style)
        
        # Parse the JSON response
        try:
            parsed_details = json.loads(event_details)
            logger.info(f"Successfully parsed JSON: {parsed_details}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {str(e)}")
            return jsonify({
                'error': 'Invalid JSON response from AI',
                'details': str(e),
                'raw_response': event_details
            }), 422
        
        # Validate the parsed details
        issues = validate_event_details(parsed_details)
        
        if issues:
            logger.warning(f"Validation issues found: {issues}")
            return jsonify({
                'error': 'Event parsing issues detected',
                'issues': issues,
                'parsed_details': parsed_details  # Include the parsed details even if there are issues
            }), 422
        
        return jsonify(parsed_details)
        
    except requests.RequestException as e:
        logger.error(f"URL fetch error: {str(e)}")
        return jsonify({
            'error': 'Failed to fetch webpage',
            'details': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Event parsing error: {str(e)}")
        return jsonify({
            'error': 'Failed to parse event details',
            'details': str(e),
            'raw_response': event_details if 'event_details' in locals() else None
        }), 500

@app.route('/create-event', methods=['POST'])
def create_event():
    event_details = request.json
    
    try:
        # Validate event details before creating
        issues = validate_event_details(event_details)
        if issues:
            return jsonify({
                'error': 'Invalid event details',
                'issues': issues
            }), 400
            
        if calendar_service is None:
            return jsonify({
                'error': 'Google Calendar is not configured'
            }), 500
        
        event = {
            'summary': event_details['title'],
            'location': event_details['location'],
            'description': event_details['description'],
            'start': {
                'dateTime': event_details['start_time'],
                'timeZone': 'America/Chicago',
            },
            'end': {
                'dateTime': event_details['end_time'],
                'timeZone': 'America/Chicago',
            },
        }

        event = calendar_service.events().insert(calendarId='cohere@wovenweb.org', body=event).execute()
        return jsonify({'eventId': event.get('id')})
    except Exception as e:
        logger.error(f"Calendar event creation error: {str(e)}")
        return jsonify({
            'error': 'Failed to create calendar event',
            'details': str(e)
        }), 500

if __name__ == '__main__':
    app.run()
