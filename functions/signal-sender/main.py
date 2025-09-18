import json
import logging
import subprocess
import tempfile
import os
from google.cloud import storage
from google.cloud import secretmanager
from flask import Request
import functions_framework

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize clients
storage_client = storage.Client()
secret_client = secretmanager.SecretManagerServiceClient()
project_id = os.environ.get('GOOGLE_CLOUD_PROJECT')

@functions_framework.http
def signal_sender(request: Request):
    """
    Cloud Function to send Signal messages.
    Uses signal-cli to send messages to Signal users.
    """
    try:
        if request.method == 'POST':
            request_json = request.get_json(silent=True)

            recipient = request_json.get('recipient')
            message = request_json.get('message')
            group_id = request_json.get('group_id')

            if not message:
                return {'error': 'message is required'}, 400

            if not recipient and not group_id:
                return {'error': 'Either recipient or group_id is required'}, 400

            return send_signal_message(recipient, message, group_id)

        elif request.method == 'GET':
            # Health check endpoint
            return {'status': 'healthy', 'service': 'signal-sender'}, 200

        else:
            return {'error': 'Method not allowed'}, 405

    except Exception as e:
        logger.error(f"Error in signal_sender: {str(e)}")
        return {'error': 'Internal server error'}, 500

def send_signal_message(recipient, message, group_id=None):
    """Send a Signal message"""
    try:
        # Get the registered phone number
        phone_number = get_registered_phone_number()
        if not phone_number:
            return {'error': 'No registered Signal number found'}, 500

        logger.info(f"Sending message from {phone_number} to {recipient or group_id}")

        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = os.path.join(temp_dir, '.local', 'share', 'signal-cli')
            os.makedirs(config_dir, exist_ok=True)

            # Restore the verified config
            restore_verified_config(phone_number, config_dir)

            # Download signal-cli
            signal_cli_path = download_signal_cli(temp_dir)

            # Build command
            cmd = [
                'java', '-jar', signal_cli_path,
                '--config', config_dir,
                'send'
            ]

            if group_id:
                cmd.extend(['--group-id', group_id])
            else:
                cmd.append(recipient)

            cmd.extend(['--message', message])

            # Send the message
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                logger.info(f"Message sent successfully to {recipient or group_id}")
                return {
                    'status': 'success',
                    'message': 'Message sent successfully',
                    'recipient': recipient,
                    'group_id': group_id
                }, 200
            else:
                logger.error(f"Message send failed: {result.stderr}")
                return {
                    'status': 'error',
                    'message': f'Send failed: {result.stderr}'
                }, 400

    except subprocess.TimeoutExpired:
        return {'status': 'error', 'message': 'Send timeout'}, 408
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        return {'status': 'error', 'message': str(e)}, 500

def get_registered_phone_number():
    """Get the registered phone number from Secret Manager"""
    try:
        secret_name = f"projects/{project_id}/secrets/signal-phone-number/versions/latest"
        response = secret_client.access_secret_version(request={"name": secret_name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        logger.error(f"Error getting phone number: {str(e)}")
        return None

def restore_verified_config(phone_number, config_dir):
    """Restore verified Signal configuration from Cloud Storage"""
    try:
        bucket_name = f"{project_id}-signal-configs"
        bucket = storage_client.bucket(bucket_name)
        blob_name = f"verified/{phone_number}/config.tar.gz"
        blob = bucket.blob(blob_name)

        tar_path = os.path.join(config_dir, 'config.tar.gz')
        blob.download_to_filename(tar_path)

        # Extract config
        import tarfile
        with tarfile.open(tar_path, 'r:gz') as tar:
            tar.extractall(config_dir)

        logger.info(f"Verified config restored for {phone_number}")

    except Exception as e:
        logger.error(f"Error restoring verified config: {str(e)}")
        raise

def download_signal_cli(temp_dir):
    """Download signal-cli binary"""
    try:
        # In a real implementation, you'd download the actual signal-cli jar
        # For this example, we'll assume it's available
        signal_cli_path = os.path.join(temp_dir, 'signal-cli.jar')

        # TODO: Download actual signal-cli jar from GitHub releases
        # For now, this is a placeholder
        logger.info("Using signal-cli binary")

        return signal_cli_path

    except Exception as e:
        logger.error(f"Error downloading signal-cli: {str(e)}")
        raise