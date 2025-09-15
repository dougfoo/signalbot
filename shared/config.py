import os
from typing import Optional

class Config:
    """Configuration settings for the Signal bot"""

    # GCP Project settings
    PROJECT_ID: str = os.environ.get('GOOGLE_CLOUD_PROJECT', '')
    REGION: str = os.environ.get('GCP_REGION', 'us-central1')

    # Pub/Sub topics
    SIGNAL_MESSAGES_TOPIC: str = 'signal-messages'
    STOCK_REQUESTS_TOPIC: str = 'stock-requests'
    RESPONSE_QUEUE_TOPIC: str = 'response-queue'

    # Firestore collections
    USERS_COLLECTION: str = 'users'
    COMMANDS_COLLECTION: str = 'commands'
    RATE_LIMITS_COLLECTION: str = 'rate_limits'

    # Rate limiting
    MAX_COMMANDS_PER_MINUTE: int = 10
    MAX_COMMANDS_PER_HOUR: int = 100

    # Stock API settings
    STOCK_CACHE_TTL_SECONDS: int = 60  # Cache stock data for 1 minute

    # Logging
    LOG_LEVEL: str = os.environ.get('LOG_LEVEL', 'INFO')

    @classmethod
    def get_pubsub_topic_path(cls, topic_name: str) -> str:
        """Get full Pub/Sub topic path"""
        return f"projects/{cls.PROJECT_ID}/topics/{topic_name}"

    @classmethod
    def get_secret_name(cls, secret_id: str) -> str:
        """Get full secret name for Secret Manager"""
        return f"projects/{cls.PROJECT_ID}/secrets/{secret_id}/versions/latest"

    @classmethod
    def validate_config(cls) -> list[str]:
        """Validate required configuration and return list of missing items"""
        missing = []

        if not cls.PROJECT_ID:
            missing.append('GOOGLE_CLOUD_PROJECT environment variable')

        return missing