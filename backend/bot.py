#!/usr/bin/env python
import os
import re
import logging
import requests
from dotenv import load_dotenv
from telegram import Update, ReactionTypeEmoji
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    MessageReactionHandler,
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

# Admin list - usernames without @ symbol
ADMIN_USERNAMES = os.getenv('ADMIN_USERNAMES', '').split(',')

# Store pending events
pending_events = {}

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

{event_details['description'][:500] + ('...' if len(event_details['description']) > 500 else '')}

👍 Admins can approve this event to add it to the calendar.
            """
            # Store the bot's response message ID instead of the original message ID
            bot_message = await update.message.reply_text(message_text)
            pending_events[bot_message.message_id] = event_details
            logger.info(f"Stored event with message ID {bot_message.message_id}")
        except Exception as e:
            logger.error("Error processing link: %s", str(e))
            # await update.message.reply_text(f"Sorry, I couldn't parse that event link. Error: {str(e)}")

async def handle_reaction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle reactions to messages."""
    logger.info("Reaction update received: %s", update)
    
    if not update.message_reaction:
        logger.info("No message_reaction in update")
        return
        
    logger.info("Reaction from user: %s", update.message_reaction.user.username)
    if not update.message_reaction.user.username in ADMIN_USERNAMES:
        logger.info("User not in admin list: %s", update.message_reaction.user.username)
        return
        
    # Check if the reaction is a thumbs up emoji
    reactions = update.message_reaction.new_reaction
    logger.info("New reactions: %s", reactions)
    
    has_thumbs_up = any(
        isinstance(reaction, ReactionTypeEmoji) and reaction.emoji == "👍"
        for reaction in reactions
    )
    logger.info("Has thumbs up: %s", has_thumbs_up)
    
    if has_thumbs_up:
        message_id = update.message_reaction.message_id
        logger.info("Message ID: %s", message_id)
        logger.info("Pending events: %s", pending_events)
        
        if message_id in pending_events:
            event_details = pending_events[message_id]
            try:
                # Post to calendar
                logger.info("Posting to calendar: %s", event_details)
                response = requests.post(f'{API_URL}/create-event', json=event_details)
                response.raise_for_status()
                
                await context.bot.send_message(
                    chat_id=update.message_reaction.chat.id,
                    text="✅ Event has been added to the calendar!"
                )
                # Remove from pending events
                del pending_events[message_id]
                logger.info("Event successfully added to calendar")
            except Exception as e:
                logger.error("Error creating calendar event: %s", str(e))
                await context.bot.send_message(
                    chat_id=update.message_reaction.chat.id,
                    text=f"❌ Failed to add event to calendar: {str(e)}"
                )

def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    application.add_handler(MessageReactionHandler(callback=handle_reaction))

    # Run the bot until the user presses Ctrl-C
    logger.info("Starting bot with allowed_updates: %s", Update.ALL_TYPES)
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
