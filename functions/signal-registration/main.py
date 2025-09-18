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
def signal_registration(request: Request):
    """
    Cloud Function to handle Signal number registration.
    Uses signal-cli binary to register and verify phone numbers.
    """
    try:
        if request.method == 'POST':
            request_json = request.get_json(silent=True)
            action = request_json.get('action')
            phone_number = request_json.get('phone_number')

            if not phone_number:
                return {'error': 'phone_number is required'}, 400

            if action == 'register':
                return register_number(phone_number)
            elif action == 'verify':
                verification_code = request_json.get('verification_code')
                if not verification_code:
                    return {'error': 'verification_code is required'}, 400
                return verify_number(phone_number, verification_code)
            else:
                return {'error': 'Invalid action. Use "register" or "verify"'}, 400

        elif request.method == 'GET':
            # Health check endpoint
            return {'status': 'healthy', 'service': 'signal-registration'}, 200

        else:
            return {'error': 'Method not allowed'}, 405

    except Exception as e:
        logger.error(f"Error in signal_registration: {str(e)}")
        return {'error': 'Internal server error'}, 500

def register_number(phone_number):
    """Register a phone number with Signal"""
    try:
        logger.info(f"Registering phone number: {phone_number}")

        # Create temporary directory for signal-cli data
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = os.path.join(temp_dir, '.local', 'share', 'signal-cli')
            os.makedirs(config_dir, exist_ok=True)

            # Download signal-cli if not available
            signal_cli_path = download_signal_cli(temp_dir)

            # Register the number
            cmd = [
                'java', '-jar', signal_cli_path,
                '--config', config_dir,
                'register', '--voice', phone_number
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                logger.info(f"Registration initiated for {phone_number}")

                # Store the config for later verification
                store_signal_config(phone_number, config_dir)

                return {
                    'status': 'success',
                    'message': f'Verification code sent to {phone_number}',
                    'phone_number': phone_number
                }, 200
            else:
                logger.error(f"Registration failed: {result.stderr}")
                return {
                    'status': 'error',
                    'message': f'Registration failed: {result.stderr}'
                }, 400

    except subprocess.TimeoutExpired:
        return {'status': 'error', 'message': 'Registration timeout'}, 408
    except Exception as e:
        logger.error(f"Error registering number: {str(e)}")
        return {'status': 'error', 'message': str(e)}, 500

def verify_number(phone_number, verification_code):
    """Verify a phone number with the received code"""
    try:
        logger.info(f"Verifying phone number: {phone_number}")

        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = os.path.join(temp_dir, '.local', 'share', 'signal-cli')
            os.makedirs(config_dir, exist_ok=True)

            # Restore the config from storage
            restore_signal_config(phone_number, config_dir)

            # Download signal-cli
            signal_cli_path = download_signal_cli(temp_dir)

            # Verify the number
            cmd = [
                'java', '-jar', signal_cli_path,
                '--config', config_dir,
                'verify', phone_number, verification_code
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                logger.info(f"Verification successful for {phone_number}")

                # Store the verified config permanently
                store_verified_config(phone_number, config_dir)

                return {
                    'status': 'success',
                    'message': f'Phone number {phone_number} verified successfully',
                    'phone_number': phone_number
                }, 200
            else:
                logger.error(f"Verification failed: {result.stderr}")
                return {
                    'status': 'error',
                    'message': f'Verification failed: {result.stderr}'
                }, 400

    except subprocess.TimeoutExpired:
        return {'status': 'error', 'message': 'Verification timeout'}, 408
    except Exception as e:
        logger.error(f"Error verifying number: {str(e)}")
        return {'status': 'error', 'message': str(e)}, 500

def download_signal_cli(temp_dir):
    """Download signal-cli binary"""
    try:
        signal_cli_url = "https://github.com/AsamK/signal-cli/releases/download/v0.12.2/signal-cli-0.12.2.tar.gz"
        signal_cli_path = os.path.join(temp_dir, 'signal-cli.jar')

        # For simplicity, use a pre-downloaded jar (in production, download from GitHub)
        # This is a placeholder - you'd need to include the jar or download it
        logger.info("Using signal-cli binary")

        return signal_cli_path

    except Exception as e:
        logger.error(f"Error downloading signal-cli: {str(e)}")
        raise

def store_signal_config(phone_number, config_dir):
    """Store Signal configuration in Cloud Storage"""
    try:
        bucket_name = f"{project_id}-signal-configs"
        bucket = storage_client.bucket(bucket_name)

        # Create bucket if it doesn't exist
        try:
            bucket.create()
        except Exception:
            pass  # Bucket already exists

        # Store config files
        blob_name = f"temp/{phone_number}/config.tar.gz"
        blob = bucket.blob(blob_name)

        # Create tar of config directory
        import tarfile
        tar_path = os.path.join(config_dir, 'config.tar.gz')
        with tarfile.open(tar_path, 'w:gz') as tar:
            tar.add(config_dir, arcname='.')

        blob.upload_from_filename(tar_path)
        logger.info(f"Config stored for {phone_number}")

    except Exception as e:
        logger.error(f"Error storing config: {str(e)}")

def restore_signal_config(phone_number, config_dir):
    """Restore Signal configuration from Cloud Storage"""
    try:
        bucket_name = f"{project_id}-signal-configs"
        bucket = storage_client.bucket(bucket_name)
        blob_name = f"temp/{phone_number}/config.tar.gz"
        blob = bucket.blob(blob_name)

        tar_path = os.path.join(config_dir, 'config.tar.gz')
        blob.download_to_filename(tar_path)

        # Extract config
        import tarfile
        with tarfile.open(tar_path, 'r:gz') as tar:
            tar.extractall(config_dir)

        logger.info(f"Config restored for {phone_number}")

    except Exception as e:
        logger.error(f"Error restoring config: {str(e)}")

def store_verified_config(phone_number, config_dir):
    """Store verified Signal configuration permanently"""
    try:
        bucket_name = f"{project_id}-signal-configs"
        bucket = storage_client.bucket(bucket_name)
        blob_name = f"verified/{phone_number}/config.tar.gz"
        blob = bucket.blob(blob_name)

        # Create tar of config directory
        import tarfile
        tar_path = os.path.join(config_dir, 'config.tar.gz')
        with tarfile.open(tar_path, 'w:gz') as tar:
            tar.add(config_dir, arcname='.')

        blob.upload_from_filename(tar_path)

        # Also store the phone number in Secret Manager
        secret_name = f"projects/{project_id}/secrets/signal-phone-number"
        try:
            secret_client.create_secret(
                request={
                    "parent": f"projects/{project_id}",
                    "secret_id": "signal-phone-number",
                    "secret": {"replication": {"automatic": {}}},
                }
            )
        except Exception:
            pass  # Secret already exists

        secret_client.add_secret_version(
            request={
                "parent": secret_name,
                "payload": {"data": phone_number.encode("UTF-8")},
            }
        )

        logger.info(f"Verified config stored permanently for {phone_number}")

    except Exception as e:
        logger.error(f"Error storing verified config: {str(e)}")