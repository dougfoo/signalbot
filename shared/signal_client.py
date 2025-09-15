import json
import logging
import requests
from google.cloud import secretmanager
import os

logger = logging.getLogger(__name__)

class SignalClient:
    """Client for interacting with Signal API"""

    def __init__(self):
        self.project_id = os.environ.get('GOOGLE_CLOUD_PROJECT')
        self.signal_api_url = self._get_signal_api_url()
        self.api_token = self._get_api_token()

    def _get_signal_api_url(self):
        """Get Signal API URL from Secret Manager"""
        try:
            client = secretmanager.SecretManagerServiceClient()
            name = f"projects/{self.project_id}/secrets/signal-api-url/versions/latest"
            response = client.access_secret_version(request={"name": name})
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            logger.error(f"Error getting Signal API URL: {e}")
            return None

    def _get_api_token(self):
        """Get Signal API token from Secret Manager"""
        try:
            client = secretmanager.SecretManagerServiceClient()
            name = f"projects/{self.project_id}/secrets/signal-api-token/versions/latest"
            response = client.access_secret_version(request={"name": name})
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            logger.error(f"Error getting Signal API token: {e}")
            return None

    def send_message(self, recipient, message, group_id=None):
        """Send a message via Signal API"""
        try:
            if not self.signal_api_url or not self.api_token:
                logger.error("Signal API credentials not configured")
                return False

            payload = {
                "message": message,
                "recipients": [recipient] if not group_id else None,
                "groupId": group_id
            }

            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }

            response = requests.post(
                f"{self.signal_api_url}/v1/send",
                json=payload,
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                logger.info(f"Message sent successfully to {recipient}")
                return True
            else:
                logger.error(f"Failed to send message: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error sending Signal message: {e}")
            return False

    def send_typing_indicator(self, recipient, group_id=None):
        """Send typing indicator"""
        try:
            if not self.signal_api_url or not self.api_token:
                return False

            payload = {
                "recipients": [recipient] if not group_id else None,
                "groupId": group_id
            }

            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }

            response = requests.post(
                f"{self.signal_api_url}/v1/typing",
                json=payload,
                headers=headers,
                timeout=10
            )

            return response.status_code == 200

        except Exception as e:
            logger.error(f"Error sending typing indicator: {e}")
            return False