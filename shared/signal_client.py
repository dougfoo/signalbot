import json
import logging
import requests
from google.cloud import secretmanager
import os

logger = logging.getLogger(__name__)

class SignalClient:
    """Client for interacting with serverless Signal functions"""

    def __init__(self):
        self.project_id = os.environ.get('GOOGLE_CLOUD_PROJECT')
        self.region = os.environ.get('GCP_REGION', 'us-central1')
        self.signal_sender_url = self._get_signal_sender_url()

    def _get_signal_sender_url(self):
        """Get Signal sender function URL"""
        try:
            # Cloud Function URL format
            return f"https://{self.region}-{self.project_id}.cloudfunctions.net/signal-sender"
        except Exception as e:
            logger.error(f"Error constructing Signal sender URL: {e}")
            return None

    def send_message(self, recipient, message, group_id=None):
        """Send a message via serverless Signal function"""
        try:
            if not self.signal_sender_url:
                logger.error("Signal sender URL not configured")
                return False

            payload = {
                "recipient": recipient,
                "message": message,
                "group_id": group_id
            }

            headers = {
                "Content-Type": "application/json"
            }

            response = requests.post(
                self.signal_sender_url,
                json=payload,
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                logger.info(f"Message sent successfully to {recipient or group_id}")
                return True
            else:
                logger.error(f"Failed to send message: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error sending Signal message: {e}")
            return False

    def send_typing_indicator(self, recipient, group_id=None):
        """Send typing indicator (placeholder for serverless implementation)"""
        # For serverless, typing indicators could be implemented as a separate function
        # For now, we'll skip this feature to keep it simple
        logger.info("Typing indicators not implemented in serverless version")
        return True