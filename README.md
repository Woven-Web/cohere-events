# Event Parser App

This application allows users to parse event details from a webpage and create Google Calendar events automatically. It features a React frontend and a Python Flask backend with AI-powered event parsing.

## Setup

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up Google Calendar API:
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project
   - Enable the Google Calendar API
   - Create OAuth 2.0 credentials
   - Download the credentials and save as `credentials.json` in the backend directory

5. Set up Anthropic API:
   - copy the `.env.sample` file to .env` in the backend directory
   - Add your Anthropic API and Telegram keys:

6. Run the backend server:
```bash
python app.py
```

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Run the development server:
```bash
npm run dev
```

## Usage

1. Open your browser and navigate to the frontend application (usually at http://localhost:5173)
2. Enter the URL of a webpage containing event details
3. Click "Parse Event" to extract the event information
4. Review and modify the extracted details if needed
5. Click "Create Event" to add the event to your Google Calendar

## Technologies Used

- Frontend:
  - React
  - Material-UI
  - Axios
  - Day.js

- Backend:
  - Flask
  - BeautifulSoup4
  - AISuite API
  - Google Calendar API

pls deploy railway