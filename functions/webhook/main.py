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
project_id = os.environ.get('GOOGLE_CLOUD_PROJECT', 'signalbot-1758169967')
topic_path = publisher.topic_path(project_id, 'signal-messages')

@functions_framework.http
def signal_webhook(request: Request):
    """
    Cloud Function to handle Signal webhook messages.
    Validates incoming requests and publishes to Pub/Sub for processing.
    """

    # Handle CORS preflight requests
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)

    try:
        # Verify request method
        if request.method == 'GET':
            response = {'status': 'healthy', 'service': 'signal-webhook', 'project': project_id}
            headers = {'Access-Control-Allow-Origin': '*'}
            return (response, 200, headers)

        if request.method != 'POST':
            headers = {'Access-Control-Allow-Origin': '*'}
            return ({'error': 'Method not allowed'}, 405, headers)

        # Get request data
        request_json = request.get_json(silent=True)
        if not request_json:
            logger.warning("No JSON payload received")
            headers = {'Access-Control-Allow-Origin': '*'}
            return ({'error': 'No JSON payload'}, 400, headers)

        # Extract message data
        envelope = request_json.get('envelope', {})
        data_message = envelope.get('dataMessage', {})

        # Check if this is a text message
        if not data_message.get('message'):
            logger.info("Ignoring non-text message")
            headers = {'Access-Control-Allow-Origin': '*'}
            return ({'status': 'ignored'}, 200, headers)

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

        headers = {'Access-Control-Allow-Origin': '*'}
        return ({'status': 'success', 'message_id': future.result(), 'message': f"Processed command: {data_message.get('message')}"}, 200, headers)

    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        headers = {'Access-Control-Allow-Origin': '*'}
        return ({'error': f'Internal server error: {str(e)}'}, 500, headers)