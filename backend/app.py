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

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, static_folder='dist', static_url_path='')
app.config['TESTING'] = True

@app.route('/')
def serve_frontend():
    return app.send_static_file('index.html')

# Catch all routes to handle React Router
@app.route('/<path:path>')
def catch_all(path):
    if path.startswith('api/'):
        return {'error': 'Not found'}, 404
    return app.send_static_file('index.html')

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

# Initialize calendar service if credentials exist
calendar_service = None
try:
    if os.path.exists('credentials.json'):
        calendar_service = get_calendar_service()
except Exception as e:
    logger.warning(f"Failed to initialize calendar service: {e}")

def validate_event_details(event_details):
    """Validate the parsed event details and return any issues."""
    required_fields = ['title', 'description', 'start_time', 'end_time', 'location']
    issues = []
    warnings = []
    
    try:
        event_dict = json.loads(event_details) if isinstance(event_details, str) else event_details
        logger.info(f"Validating event details: {event_dict}")
        
        # Check for missing fields
        for field in required_fields:
            if field not in event_dict:
                issues.append(f"Missing required field: {field}")
            elif not event_dict[field]:
                warnings.append(f"Empty value for field: {field}")
        
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
        
        return {'errors': issues, 'warnings': warnings}
    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        return {'errors': [str(e)], 'warnings': []}

def parse_event_with_ai(page_content, source_url, description_style="default"):
    client = ai.Client()
    
    description_prompts = {
        "default": "A comprehensive description that includes all relevant details about the event. Include any important information like agenda, speakers, requirements, or special notes.",
        "telegram": "A brief, concise summary of the event (2-3 sentences max) highlighting only the most important details. Focus on what, when, and why someone might want to attend."
    }
    
    description_prompt = description_prompts.get(description_style, description_prompts["default"])
    
    prompt = f"""Extract event details from the following webpage content and return ONLY a JSON object with these fields:
    - title: event title
    - description: {description_prompt} Start the description with 'Source: {source_url}\n\n' followed by the description.
    - start_time: start time in ISO format
    - end_time: end time in ISO format
    - location: event location

    IMPORTANT: Return ONLY the JSON object with NO explanatory text before or after. The response must be valid JSON that can be parsed directly.

    Webpage content:
    {page_content}
    """
    
    messages = [{
        "role": "system",
        "content": "You are an AI assistant that helps users parse events from webpages. Return ONLY valid JSON with the specified fields, with no additional text. Use ISO format for dates (YYYY-MM-DDTHH:MM:SS+HH:MM). For descriptions, be comprehensive and include all relevant details from the source, properly formatted for readability."
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
        
        # Clean up the response to extract just the JSON object
        content = response.choices[0].message.content.strip()
        
        return content
    except Exception as e:
        logger.error(e)
        logger.error(f"AI parsing error: {str(e)}")
        raise

def clean_json_response(content):
    """Clean up AI response to extract just the JSON object"""
    content = content.strip()
    
    # Remove common LLM prefixes
    prefixes_to_remove = [
        "Here is the JSON object with the extracted event details:",
        "Here's the JSON object:",
        "Here is a JSON object with the extracted event details:",
        "Here is the event information in JSON format:",
        "The extracted event details in JSON format:"
    ]
    
    for prefix in prefixes_to_remove:
        if content.lower().startswith(prefix.lower()):
            content = content[len(prefix):].strip()
    
    # Remove any markdown code block formatting
    if content.startswith("```json"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    
    return content.strip()

def get_page_content(url):
    """Fetch webpage content"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
        'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        'Referer': 'https://app.actualize.earth/',
        'Origin': 'https://app.actualize.earth',
        'Host': 'app.actualize.earth',
        'Connection': 'keep-alive'
    }

    # Customize headers based on the domain
    domain = url.split('/')[2]
    if domain != 'app.actualize.earth':
        # Remove site-specific headers for other domains
        headers.pop('Referer', None)
        headers.pop('Origin', None)
        headers.pop('Host', None)

    session = requests.Session()
    try:
        response = session.get(url, headers=headers, allow_redirects=True)
        response.raise_for_status()
        return response.text
    except requests.exceptions.SSLError:
        logger.warning(f"SSL verification failed for {url}, retrying without verification")
        # If SSL verification fails, try again without verification
        response = session.get(url, headers=headers, allow_redirects=True, verify=False)
        response.raise_for_status()
        return response.text

@app.route('/parse-event', methods=['POST'])
def parse_event():
    url = request.json.get('url')
    description_style = request.json.get('description_style', 'default')
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    try:
        # Fetch webpage content
        logger.info(f"Fetching content from URL: {url}")
        page_content = get_page_content(url)
        
        soup = BeautifulSoup(page_content, 'html.parser')
        
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
        
        # Clean up and parse the JSON response
        try:
            cleaned_response = clean_json_response(event_details)
            parsed_details = json.loads(cleaned_response)
            logger.info(f"Successfully parsed JSON: {parsed_details}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {str(e)}")
            return jsonify({
                'error': 'Invalid JSON response from AI',
                'details': str(e),
                'raw_response': event_details,
                'cleaned_response': cleaned_response if 'cleaned_response' in locals() else None
            }), 422
        
        # Validate the parsed details
        validation_result = validate_event_details(parsed_details)
        
        if validation_result['errors']:
            logger.warning(f"Validation issues found: {validation_result}")
            return jsonify({
                'error': 'Event parsing issues detected',
                'issues': validation_result['errors'],
                'warnings': validation_result['warnings'],
                'parsed_details': parsed_details  # Include the parsed details even if there are issues
            }), 422
        
        # If we only have warnings, return 200 with warnings
        if validation_result['warnings']:
            logger.info(f"Validation warnings found: {validation_result['warnings']}")
            return jsonify({
                'warnings': validation_result['warnings'],
                **parsed_details
            })
        
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
        if issues['errors']:
            return jsonify({
                'error': 'Invalid event details',
                'issues': issues['errors']
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

        event = calendar_service.events().insert(calendarId='cohere@unforced.org', body=event).execute()
        return jsonify({'eventId': event.get('id')})
    except Exception as e:
        logger.error(f"Calendar event creation error: {str(e)}")
        return jsonify({
            'error': 'Failed to create calendar event',
            'details': str(e)
        }), 500

if __name__ == '__main__':
    app.run()
