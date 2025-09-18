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
            route_stock_command(sender, args, group_id)
        elif command == '/help':
            route_help_command(sender, group_id)
        else:
            send_unknown_command_response(sender, command, group_id)

        # Log command usage
        log_command_usage(sender, command, args, group_id)

        # Send acknowledgment for group chats
        if group_id:
            send_response(sender, f"Processing {command} command...", group_id)

    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")

def route_stock_command(sender, args, group_id):
    """Route stock command to stock handler function"""
    if not args:
        send_response(sender, "Usage: /stock <ticker>\nExample: /stock AAPL", group_id)
        return

    ticker = args[0].upper()
    if not re.match(r'^[A-Z]{1,5}$', ticker):
        send_response(sender, "Invalid ticker symbol. Please use 1-5 letters.", group_id)
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

def route_help_command(sender, group_id):
    """Send help message"""
    context = "group chat" if group_id else "direct message"
    help_text = f"""🤖 Signal Stock Bot - Available Commands

📈 /stock <ticker> - Get real-time stock price
   Examples: /stock AAPL, /stock TSLA, /stock MSFT

ℹ️  /help - Show this help message

💡 Usage in {context}:
   • Bot responds to all group members
   • Commands work the same in DM or group
   • Stock data updates every request

🚀 Try: /stock AAPL"""

    send_response(sender, help_text, group_id)

def send_unknown_command_response(sender, command, group_id):
    """Send response for unknown commands"""
    response = f"Unknown command: {command}\nType /help for available commands."
    send_response(sender, response, group_id)

def send_response(sender, message, group_id):
    """Send response back to Signal"""
    # This would integrate with Signal API to send messages
    # For now, we'll log the response
    logger.info(f"Sending response to {sender}: {message}")
    # TODO: Implement actual Signal API response

def log_command_usage(sender, command, args, group_id):
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