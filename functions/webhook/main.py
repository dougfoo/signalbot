import json
import logging
from google.cloud import pubsub_v1
from flask import Request
import functions_framework
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Pub/Sub client
publisher = pubsub_v1.PublisherClient()
project_id = os.environ.get('GOOGLE_CLOUD_PROJECT')
topic_path = publisher.topic_path(project_id, 'signal-messages')

@functions_framework.http
def signal_webhook(request: Request):
    """
    Cloud Function to handle Signal webhook messages.
    Validates incoming requests and publishes to Pub/Sub for processing.
    """
    try:
        # Verify request method
        if request.method != 'POST':
            return {'error': 'Method not allowed'}, 405

        # Get request data
        request_json = request.get_json(silent=True)
        if not request_json:
            logger.warning("No JSON payload received")
            return {'error': 'No JSON payload'}, 400

        # Extract message data
        envelope = request_json.get('envelope', {})
        data_message = envelope.get('dataMessage', {})

        # Check if this is a text message
        if not data_message.get('message'):
            logger.info("Ignoring non-text message")
            return {'status': 'ignored'}, 200

        # Prepare message for Pub/Sub
        message_data = {
            'timestamp': envelope.get('timestamp'),
            'source': envelope.get('source'),
            'message': data_message.get('message'),
            'group_id': data_message.get('groupInfo', {}).get('groupId')
        }

        # Publish to Pub/Sub
        message_json = json.dumps(message_data)
        future = publisher.publish(topic_path, message_json.encode('utf-8'))

        logger.info(f"Message published to Pub/Sub: {future.result()}")

        return {'status': 'success', 'message_id': future.result()}, 200

    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return {'error': 'Internal server error'}, 500