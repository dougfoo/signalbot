#!/bin/bash

# Deploy signal-api to Google Cloud VM
# This script creates a VM and sets up signal-api automatically

set -e

# Configuration
PROJECT_ID="signalbot-1758169967"
ZONE="us-central1-a"
INSTANCE_NAME="signal-api-server"
MACHINE_TYPE="e2-micro"

print_status() {
    echo -e "\033[32m[INFO]\033[0m $1"
}

print_error() {
    echo -e "\033[31m[ERROR]\033[0m $1"
}

# Set gcloud path for Windows
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    export GCLOUD_CMD="/c/Users/dougc/google-cloud-sdk/bin/gcloud.cmd"
else
    export GCLOUD_CMD="gcloud"
fi

create_vm() {
    print_status "Creating VM instance..."

    "$GCLOUD_CMD" compute instances create $INSTANCE_NAME \
        --zone=$ZONE \
        --machine-type=$MACHINE_TYPE \
        --image-family=ubuntu-2004-lts \
        --image-project=ubuntu-os-cloud \
        --tags=http-server,signal-api \
        --metadata=startup-script='#!/bin/bash
            apt-get update
            apt-get install -y docker.io docker-compose git
            systemctl start docker
            systemctl enable docker
            usermod -aG docker $USER

            # Clone repository
            cd /opt
            git clone https://github.com/dougfoo/signalbot.git
            cd signalbot/signal-api-server

            # Start signal-api
            docker-compose up -d
        ' \
        --project=$PROJECT_ID
}

create_firewall_rule() {
    print_status "Creating firewall rule for signal-api..."

    "$GCLOUD_CMD" compute firewall-rules create allow-signal-api \
        --allow tcp:8080 \
        --source-ranges 0.0.0.0/0 \
        --target-tags signal-api \
        --description="Allow Signal API access" \
        --project=$PROJECT_ID || true
}

get_external_ip() {
    print_status "Getting external IP..."

    EXTERNAL_IP=$("$GCLOUD_CMD" compute instances describe $INSTANCE_NAME \
        --zone=$ZONE \
        --format="get(networkInterfaces[0].accessConfigs[0].natIP)" \
        --project=$PROJECT_ID)

    echo "External IP: $EXTERNAL_IP"
}

show_next_steps() {
    print_status "🎉 Signal API server deployed successfully!"
    echo ""
    echo "📱 Next steps:"
    echo "1. Wait 2-3 minutes for the server to start up"
    echo "2. Register your phone number:"
    echo "   curl -X POST http://$EXTERNAL_IP:8080/v1/register/+81804142-7606"
    echo ""
    echo "3. Verify with SMS code:"
    echo "   curl -X POST http://$EXTERNAL_IP:8080/v1/register/+81804142-7606/verify/SMS_CODE"
    echo ""
    echo "4. Test the API:"
    echo "   curl http://$EXTERNAL_IP:8080/v1/about"
    echo ""
    echo "🌐 Signal API URL: http://$EXTERNAL_IP:8080"
    echo "🔗 Webhook configured to: https://signal-webhook-vt72tbrjvq-uc.a.run.app"
    echo ""
    echo "💰 Estimated cost: ~$3-5/month"
}

main() {
    print_status "🚀 Deploying Signal API to Google Cloud VM..."

    "$GCLOUD_CMD" config set project $PROJECT_ID

    create_vm
    create_firewall_rule
    sleep 10  # Wait for VM to get IP
    get_external_ip
    show_next_steps
}

main "$@"