# Cohere Events

A web application and Telegram bot for parsing and managing event details from various platforms.

## Local Development Setup

### Prerequisites
- Python 3.8+
- Node.js 16+
- npm

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/cohere-events.git
cd cohere-events
```

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

3. Set up the frontend:
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install
```

4. Configure your `.env` file with required API keys

## Running Locally

### Development Mode (with auto-reload)

1. Build the frontend with watch mode:
```bash
cd frontend
npm run build
```
The frontend will automatically rebuild when you make changes.

2. Run the Flask development server:
```bash
cd backend
python app.py
```

The application will be available at http://localhost:5000

### Production Mode

Run the Flask application using Gunicorn:
```bash
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
gunicorn wsgi:app --bind 127.0.0.1:5000
```

### Telegram Bot (Optional)
In a separate terminal:
```bash
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
python bot.py
```

## Railway Deployment

Before deploying:
1. Build the frontend locally: `cd frontend && npm install && npm run build`
2. Create a static directory in backend and copy the built files:
   ```bash
   mkdir -p backend/static
   cp -r frontend/dist/* backend/static/
   ```
3. Commit and push your changes

### 1. Flask Web Service
1. Create a new service pointing to your repository
2. Set the root directory to `/backend`
3. Set the build command: `pip install -r requirements.txt`
4. Set the start command: `gunicorn wsgi:app --bind 0.0.0.0:8080`
5. Add environment variables:
   - `ANTHROPIC_API_KEY`

### 2. Telegram Bot Service
1. Create another service pointing to the same repository
2. Set the root directory to `/backend`
3. Set the start command: `python bot.py`
4. Add environment variables:
   - `TELEGRAM_BOT_TOKEN`
   - `API_URL`: Set to `https://${flask api + web app.RAILWAY_PUBLIC_DOMAIN}`
5. Add service dependency:
   - Go to Settings > Dependencies
   - Add the Flask service as a dependency

Railway will ensure the Flask service is running before starting the bot service.

## Architecture

- Frontend: React + Vite
- Backend: Flask
- The frontend builds directly into the backend's static directory
- Auto-rebuilds on frontend changes for seamless development
- Optional Telegram bot integration

## Features

- Parse event details from Partiful links
- Create Google Calendar events with parsed details
- Timezone-aware event handling
- Clean, modern UI
- Telegram bot integration for easy event parsing

## Environment Variables

Required variables in `.env`:
- `ANTHROPIC_API_KEY`: Your Anthropic API key
- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token (only if using bot)

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

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request