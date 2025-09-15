import json
import logging
import base64
from google.cloud import pubsub_v1
from google.cloud import firestore
import functions_framework
import os
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize clients
publisher = pubsub_v1.PublisherClient()
db = firestore.Client()
project_id = os.environ.get('GOOGLE_CLOUD_PROJECT')

@functions_framework.cloud_event
def process_message(cloud_event):
    """
    Cloud Function triggered by Pub/Sub to process Signal messages.
    Parses commands and routes to appropriate handlers.
    """
    try:
        # Decode Pub/Sub message
        pubsub_message = base64.b64decode(cloud_event.data["message"]["data"])
        message_data = json.loads(pubsub_message.decode('utf-8'))

        logger.info(f"Processing message: {message_data}")

        # Extract message details
        sender = message_data.get('source')
        message_text = message_data.get('message', '').strip()
        group_id = message_data.get('group_id')

        # Check if message is a command (starts with /)
        if not message_text.startswith('/'):
            logger.info("Message is not a command, ignoring")
            return

        # Parse command
        command_parts = message_text.split()
        command = command_parts[0].lower()
        args = command_parts[1:] if len(command_parts) > 1 else []

        # Route commands
        if command == '/stock':
            await route_stock_command(sender, args, group_id)
        elif command == '/help':
            await route_help_command(sender, group_id)
        else:
            await send_unknown_command_response(sender, command, group_id)

        # Log command usage
        await log_command_usage(sender, command, args, group_id)

    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")

async def route_stock_command(sender, args, group_id):
    """Route stock command to stock handler function"""
    if not args:
        await send_response(sender, "Usage: /stock <ticker>\nExample: /stock AAPL", group_id)
        return

    ticker = args[0].upper()
    if not re.match(r'^[A-Z]{1,5}$', ticker):
        await send_response(sender, "Invalid ticker symbol. Please use 1-5 letters.", group_id)
        return

    # Publish to stock handler
    topic_path = publisher.topic_path(project_id, 'stock-requests')
    stock_request = {
        'sender': sender,
        'ticker': ticker,
        'group_id': group_id
    }

    future = publisher.publish(topic_path, json.dumps(stock_request).encode('utf-8'))
    logger.info(f"Stock request published: {future.result()}")

async def route_help_command(sender, group_id):
    """Send help message"""
    help_text = """Available commands:
/stock <ticker> - Get current stock price (e.g., /stock AAPL)
/help - Show this help message

Example: /stock TSLA"""

    await send_response(sender, help_text, group_id)

async def send_unknown_command_response(sender, command, group_id):
    """Send response for unknown commands"""
    response = f"Unknown command: {command}\nType /help for available commands."
    await send_response(sender, response, group_id)

async def send_response(sender, message, group_id):
    """Send response back to Signal"""
    # This would integrate with Signal API to send messages
    # For now, we'll log the response
    logger.info(f"Sending response to {sender}: {message}")
    # TODO: Implement actual Signal API response

async def log_command_usage(sender, command, args, group_id):
    """Log command usage to Firestore"""
    try:
        doc_ref = db.collection('commands').document()
        doc_ref.set({
            'sender': sender,
            'command': command,
            'args': args,
            'group_id': group_id,
            'timestamp': firestore.SERVER_TIMESTAMP
        })
    except Exception as e:
        logger.error(f"Error logging command: {str(e)}")