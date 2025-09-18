#!/bin/bash

# Signal Bot GCP Deployment Script
# This script deploys the Signal bot AND Signal API to Google Cloud Platform

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID=""
REGION="us-central1"
TERRAFORM_DIR="terraform"
FUNCTIONS_DIR="functions"

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

    # Check if gcloud is installed
    if ! command -v gcloud &> /dev/null; then
        print_error "gcloud CLI is not installed. Please install it first."
        exit 1
    fi

    # Check if terraform is installed
    if ! command -v terraform &> /dev/null; then
        print_error "Terraform is not installed. Please install it first."
        exit 1
    fi

    # Check if zip is installed
    if ! command -v zip &> /dev/null; then
        print_error "zip is not installed. Please install it first."
        exit 1
    fi

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
    gcloud config set project $PROJECT_ID

    # Enable required APIs
    print_status "Enabling required APIs..."
    gcloud services enable cloudfunctions.googleapis.com \
        pubsub.googleapis.com \
        firestore.googleapis.com \
        secretmanager.googleapis.com \
        cloudbuild.googleapis.com \
        storage.googleapis.com
}

package_functions() {
    print_status "Packaging Cloud Functions..."

    cd $FUNCTIONS_DIR

    # Package webhook function
    print_status "Packaging webhook function..."
    cd webhook
    zip -r ../../webhook-source.zip . -x "*.pyc" "__pycache__/*"
    cd ..

    # Package message processor function
    print_status "Packaging message processor function..."
    cd message-processor
    zip -r ../../message-processor-source.zip . -x "*.pyc" "__pycache__/*"
    cd ..

    # Package stock handler function
    print_status "Packaging stock handler function..."
    cd stock-handler
    zip -r ../../stock-handler-source.zip . -x "*.pyc" "__pycache__/*"
    cd ..

    cd ..
    print_status "Function packaging complete!"
}

deploy_infrastructure() {
    print_status "Deploying infrastructure with Terraform..."

    cd $TERRAFORM_DIR

    # Initialize Terraform
    terraform init

    # Plan deployment
    terraform plan -var="project_id=$PROJECT_ID" -var="region=$REGION"

    # Apply deployment
    print_status "Applying Terraform configuration..."
    terraform apply -var="project_id=$PROJECT_ID" -var="region=$REGION" -auto-approve

    cd ..
    print_status "Infrastructure deployment complete!"
}

upload_function_sources() {
    print_status "Uploading function source code..."

    BUCKET_NAME="${PROJECT_ID}-signal-bot-functions"

    # Upload function source files
    gsutil cp webhook-source.zip gs://$BUCKET_NAME/
    gsutil cp message-processor-source.zip gs://$BUCKET_NAME/
    gsutil cp stock-handler-source.zip gs://$BUCKET_NAME/
    gsutil cp signal-registration-source.zip gs://$BUCKET_NAME/
    gsutil cp signal-sender-source.zip gs://$BUCKET_NAME/

    print_status "Function source upload complete!"
}

package_signal_functions() {
    print_status "Packaging Signal functions..."

    cd $FUNCTIONS_DIR

    # Package signal registration function
    print_status "Packaging signal registration function..."
    cd signal-registration
    zip -r ../../signal-registration-source.zip . -x "*.pyc" "__pycache__/*"
    cd ..

    # Package signal sender function
    print_status "Packaging signal sender function..."
    cd signal-sender
    zip -r ../../signal-sender-source.zip . -x "*.pyc" "__pycache__/*"
    cd ..

    cd ..
    print_status "Signal function packaging complete!"
}

show_next_steps() {
    print_status "Deployment complete! Next steps:"
    echo ""

    # Get function URLs
    cd $TERRAFORM_DIR
    WEBHOOK_URL=$(terraform output -raw webhook_url)
    REGISTRATION_URL=$(terraform output -raw signal_registration_url)
    SENDER_URL=$(terraform output -raw signal_sender_url)
    cd ..

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
    echo "🤖 STEP 2: Set up Signal webhook (point to this URL):"
    echo "   $WEBHOOK_URL"
    echo ""
    echo "🧪 STEP 3: Test your bot:"
    echo "   Send '/stock AAPL' to your registered Signal number"
    echo ""
    echo "📊 Function URLs:"
    echo "   - Webhook: $WEBHOOK_URL"
    echo "   - Registration: $REGISTRATION_URL"
    echo "   - Sender: $SENDER_URL"
}

cleanup() {
    print_status "Cleaning up temporary files..."
    rm -f webhook-source.zip message-processor-source.zip stock-handler-source.zip signal-registration-source.zip signal-sender-source.zip
}

main() {
    if [ $# -eq 1 ]; then
        PROJECT_ID=$1
    fi

    print_status "Starting Signal Bot deployment..."

    check_prerequisites
    setup_gcp_project
    package_functions
    package_signal_functions
    deploy_infrastructure
    upload_function_sources
    cleanup
    show_next_steps

    # Get webhook URL
    cd $TERRAFORM_DIR
    WEBHOOK_URL=$(terraform output -raw webhook_url)
    cd ..

    print_status "Your webhook URL is: $WEBHOOK_URL"
}

# Run the main function
main "$@"