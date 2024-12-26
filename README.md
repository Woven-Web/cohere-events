# Event Parser App

This application allows users to parse event details from a webpage and create Google Calendar events automatically. It features a React frontend and a Python Flask backend with AI-powered event parsing.

## Setup

1. Clone the repository

2. Set up the backend:
```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.sample .env
```

3. Configure your `.env` file with required API keys

## Running the Application

The application consists of two components that need to be run separately:

### 1. Flask Web Server

Run the Flask application using Gunicorn (make sure your virtual environment is activated):
```bash
# If not already in backend directory
cd backend

# Activate virtual environment if not already activated
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Start the server
gunicorn wsgi:app --bind 127.0.0.1:5000
```

This will start the web server at http://127.0.0.1:5000

### 2. Telegram Bot

In a separate terminal, run the Telegram bot (make sure your virtual environment is activated):
```bash
# If not already in backend directory
cd backend

# Activate virtual environment if not already activated
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Start the bot
python bot.py
```

The bot will start and listen for messages containing event links.

## Railway Deployment

The application requires two services on Railway:

### 1. Flask Web Service
1. Create a new service pointing to your repository
2. Set the start command: `gunicorn wsgi:app --bind 0.0.0.0:$PORT`
3. Add environment variables:
   - `ANTHROPIC_API_KEY`

### 2. Telegram Bot Service
1. Create another service pointing to the same repository
2. Set the start command: `python bot.py`
3. Add environment variables:
   - `TELEGRAM_BOT_TOKEN`
   - `API_URL`: Set to `https://${RAILWAY_STATIC_URL}/api`
4. Add service dependency:
   - Go to Settings > Dependencies
   - Add the Flask service as a dependency

Railway will ensure the Flask service is running before starting the bot service.

## Usage

### Web Interface
- Visit http://127.0.0.1:5000 (or your Railway URL)
- Paste an event URL to parse event details

### Telegram Bot
1. Start a chat with the bot
2. Send `/start` to begin
3. Send any event URL to get parsed details
4. The bot will react with 👀 when processing your link

## Environment Variables

- `ANTHROPIC_API_KEY`: Your Anthropic API key
- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token

## Frontend Development

For frontend development:

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

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