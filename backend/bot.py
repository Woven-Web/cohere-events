#!/usr/bin/env python
import os
import re
import logging
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# Set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
API_URL = os.getenv('API_URL', 'http://127.0.0.1:8080').rstrip('/')  # Default to port 8080 to match Railway

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    logger.info("Start command received!")
    await update.message.reply_text("Hi! Send me an event link and I'll parse it for you!")

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle messages containing URLs."""
    logger.info("Handle link called: %s", update.message.text)
    message = update.message.text
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    urls = re.findall(url_pattern, message)
    
    if urls:
        # Add eyes reaction to acknowledge URL detection
        await update.message.set_reaction("👀")
        url = urls[0]
        try:
            # Make request to our parse-event endpoint
            response = requests.post(f'{API_URL}/parse-event', 
                                  json={'url': url, 'description_style': 'telegram'})
            response.raise_for_status()
            
            event_details = response.json()
            # Send formatted message to Telegram
            message_text = f"""
Event Detected! 🎉
Title: {event_details['title']}
Time: {event_details['start_time']} - {event_details['end_time']}
Location: {event_details['location']}

{event_details['description'][:500]}...
            """
            await update.message.reply_text(message_text)
        except Exception as e:
            logger.error("Error processing link: %s", str(e))
            await update.message.reply_text(f"Sorry, I couldn't parse that event link. Error: {str(e)}")

def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))

    # Run the bot until the user presses Ctrl-C
    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
