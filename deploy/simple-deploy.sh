#!/bin/bash

# Simple Signal Bot GCP Deployment Script
# Uses only gcloud CLI - no Terraform needed!

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID=""
REGION="us-central1"

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    print_status "Checking prerequisites..."

    # Set gcloud path for Windows
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
        export GCLOUD_CMD="/c/Users/dougc/google-cloud-sdk/bin/gcloud.cmd"
    else
        export GCLOUD_CMD="gcloud"
    fi

    if ! command -v "$GCLOUD_CMD" &> /dev/null && ! [[ -f "$GCLOUD_CMD" ]]; then
        print_error "gcloud CLI is not found. Please install it first:"
        echo "https://cloud.google.com/sdk/docs/install"
        exit 1
    fi

    # zip is not required for gcloud functions deploy - it handles packaging automatically

    print_status "Prerequisites check passed!"
}

setup_gcp_project() {
    if [ -z "$PROJECT_ID" ]; then
        print_error "Please set PROJECT_ID in the script or pass it as an argument"
        echo "Usage: $0 [PROJECT_ID]"
        exit 1
    fi

    print_status "Setting up GCP project: $PROJECT_ID"

    # Set the project
    "$GCLOUD_CMD" config set project $PROJECT_ID

    # Enable required APIs
    print_status "Enabling required APIs..."
    "$GCLOUD_CMD" services enable \
        cloudfunctions.googleapis.com \
        pubsub.googleapis.com \
        firestore.googleapis.com \
        secretmanager.googleapis.com \
        cloudbuild.googleapis.com \
        storage.googleapis.com \
        run.googleapis.com \
        eventarc.googleapis.com
}

create_resources() {
    print_status "Creating GCP resources..."

    # Create Pub/Sub topics
    print_status "Creating Pub/Sub topics..."
    "$GCLOUD_CMD" pubsub topics create signal-messages || true
    "$GCLOUD_CMD" pubsub topics create stock-requests || true
    "$GCLOUD_CMD" pubsub topics create response-queue || true

    # Create storage buckets
    print_status "Creating storage buckets..."
    "$GCLOUD_CMD" storage buckets create gs://${PROJECT_ID}-signal-configs || true
    "$GCLOUD_CMD" storage buckets create gs://${PROJECT_ID}-function-source || true

    # Create secrets
    print_status "Creating secrets..."
    "$GCLOUD_CMD" secrets create signal-phone-number --replication-policy="automatic" || true

    print_status "Resources created!"
}

deploy_functions() {
    print_status "Deploying Cloud Functions..."

    # Deploy webhook function
    print_status "Deploying webhook function..."
    "$GCLOUD_CMD" functions deploy signal-webhook \
        --gen2 \
        --runtime=python311 \
        --region=$REGION \
        --source=functions/webhook \
        --entry-point=signal_webhook \
        --trigger-http \
        --allow-unauthenticated \
        --memory=256MB \
        --timeout=60s

    # Deploy message processor function
    print_status "Deploying message processor function..."
    "$GCLOUD_CMD" functions deploy message-processor \
        --gen2 \
        --runtime=python311 \
        --region=$REGION \
        --source=functions/message-processor \
        --entry-point=process_message \
        --trigger-topic=signal-messages \
        --memory=256MB \
        --timeout=60s

    # Deploy stock handler function
    print_status "Deploying stock handler function..."
    "$GCLOUD_CMD" functions deploy stock-handler \
        --gen2 \
        --runtime=python311 \
        --region=$REGION \
        --source=functions/stock-handler \
        --entry-point=handle_stock_request \
        --trigger-topic=stock-requests \
        --memory=512MB \
        --timeout=120s

    # Deploy signal registration function
    print_status "Deploying signal registration function..."
    "$GCLOUD_CMD" functions deploy signal-registration \
        --gen2 \
        --runtime=python311 \
        --region=$REGION \
        --source=functions/signal-registration \
        --entry-point=signal_registration \
        --trigger-http \
        --allow-unauthenticated \
        --memory=512MB \
        --timeout=180s

    # Deploy signal sender function
    print_status "Deploying signal sender function..."
    "$GCLOUD_CMD" functions deploy signal-sender \
        --gen2 \
        --runtime=python311 \
        --region=$REGION \
        --source=functions/signal-sender \
        --entry-point=signal_sender \
        --trigger-http \
        --allow-unauthenticated \
        --memory=512MB \
        --timeout=120s

    print_status "All functions deployed!"
}

show_next_steps() {
    print_status "🎉 Deployment complete! Here's what to do next:"
    echo ""

    # Get function URLs
    WEBHOOK_URL=$("$GCLOUD_CMD" functions describe signal-webhook --region=$REGION --gen2 --format="value(serviceConfig.uri)")
    REGISTRATION_URL=$("$GCLOUD_CMD" functions describe signal-registration --region=$REGION --gen2 --format="value(serviceConfig.uri)")

    echo "📱 STEP 1: Register your Signal phone number"
    echo "   curl -X POST \"$REGISTRATION_URL\" \\"
    echo "     -H \"Content-Type: application/json\" \\"
    echo "     -d '{\"action\": \"register\", \"phone_number\": \"+1234567890\"}'"
    echo ""
    echo "   # After receiving SMS code:"
    echo "   curl -X POST \"$REGISTRATION_URL\" \\"
    echo "     -H \"Content-Type: application/json\" \\"
    echo "     -d '{\"action\": \"verify\", \"phone_number\": \"+1234567890\", \"verification_code\": \"123456\"}'"
    echo ""
    echo "🤖 STEP 2: Set up Signal webhook (point Signal to this URL):"
    echo "   $WEBHOOK_URL"
    echo ""
    echo "🧪 STEP 3: Test your bot:"
    echo "   Send '/stock AAPL' to your registered Signal number"
    echo ""
    echo "📊 Your function URLs:"
    echo "   - Webhook: $WEBHOOK_URL"
    echo "   - Registration: $REGISTRATION_URL"
    echo ""
    print_warning "Save these URLs! You'll need them for Signal setup."
}

main() {
    if [ $# -eq 1 ]; then
        PROJECT_ID=$1
    fi

    print_status "🚀 Starting Simple Signal Bot deployment..."

    check_prerequisites
    setup_gcp_project
    create_resources
    deploy_functions
    show_next_steps

    print_status "✅ Deployment complete! No Terraform needed!"
}

# Run the main function
main "$@"