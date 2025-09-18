#!/bin/bash

# Direct signal-cli setup without Docker
# This script installs signal-cli directly on Ubuntu VM

set -e

print_status() {
    echo -e "\033[32m[INFO]\033[0m $1"
}

setup_signal_cli() {
    print_status "Setting up signal-cli without Docker..."

    # Update system
    sudo apt update

    # Install Java (required for signal-cli)
    sudo apt install -y openjdk-17-jre wget curl

    # Download signal-cli
    cd /opt
    sudo wget https://github.com/AsamK/signal-cli/releases/download/v0.12.8/signal-cli-0.12.8.tar.gz
    sudo tar xf signal-cli-0.12.8.tar.gz
    sudo ln -sf /opt/signal-cli-0.12.8/bin/signal-cli /usr/local/bin/signal-cli

    print_status "signal-cli installed successfully!"
}

create_webhook_forwarder() {
    print_status "Creating webhook forwarder service..."

    # Create a simple Python webhook forwarder
    sudo tee /opt/webhook-forwarder.py > /dev/null << 'EOF'
#!/usr/bin/env python3
import json
import requests
import subprocess
import time
import sys
from datetime import datetime

WEBHOOK_URL = "https://signal-webhook-vt72tbrjvq-uc.a.run.app"
PHONE_NUMBER = "+81804142-7606"

def check_messages():
    """Check for new messages using signal-cli"""
    try:
        cmd = ["signal-cli", "-a", PHONE_NUMBER, "receive", "--json"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    try:
                        message = json.loads(line)
                        if message.get('envelope', {}).get('dataMessage', {}).get('message'):
                            forward_to_webhook(message)
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        print(f"Error checking messages: {e}")

def forward_to_webhook(message):
    """Forward message to our GCP webhook"""
    try:
        response = requests.post(WEBHOOK_URL, json=message, timeout=10)
        print(f"Forwarded message to webhook: {response.status_code}")
    except Exception as e:
        print(f"Error forwarding to webhook: {e}")

def main():
    print(f"Starting webhook forwarder for {PHONE_NUMBER}")
    print(f"Forwarding to: {WEBHOOK_URL}")

    while True:
        try:
            check_messages()
            time.sleep(5)  # Check every 5 seconds
        except KeyboardInterrupt:
            print("Shutting down...")
            break
        except Exception as e:
            print(f"Error in main loop: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
EOF

    sudo chmod +x /opt/webhook-forwarder.py

    # Install Python dependencies
    sudo apt install -y python3-pip
    sudo pip3 install requests

    print_status "Webhook forwarder created!"
}

create_systemd_service() {
    print_status "Creating systemd service..."

    sudo tee /etc/systemd/system/signal-webhook.service > /dev/null << 'EOF'
[Unit]
Description=Signal Webhook Forwarder
After=network.target

[Service]
Type=simple
User=signal
Group=signal
WorkingDirectory=/opt
ExecStart=/usr/bin/python3 /opt/webhook-forwarder.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    # Create signal user
    sudo useradd -r -s /bin/false signal || true
    sudo chown signal:signal /opt/webhook-forwarder.py

    # Enable and start service
    sudo systemctl daemon-reload
    sudo systemctl enable signal-webhook.service

    print_status "Systemd service created!"
}

show_next_steps() {
    print_status "🎉 Signal-cli setup complete!"
    echo ""
    echo "📱 Next steps:"
    echo "1. Register your phone number:"
    echo "   sudo signal-cli register +81804142-7606"
    echo ""
    echo "2. Verify with SMS code:"
    echo "   sudo signal-cli verify +81804142-7606 SMS_CODE"
    echo ""
    echo "3. Start the webhook forwarder:"
    echo "   sudo systemctl start signal-webhook.service"
    echo ""
    echo "4. Check service status:"
    echo "   sudo systemctl status signal-webhook.service"
    echo ""
    echo "5. Test by sending '/stock AAPL' to +81804142-7606"
}

main() {
    setup_signal_cli
    create_webhook_forwarder
    create_systemd_service
    show_next_steps
}

main "$@"