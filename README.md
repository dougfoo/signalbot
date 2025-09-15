# Signal Stock Bot - GCP Serverless

A serverless Signal chatbot built on Google Cloud Platform that responds to stock ticker commands.

## Features

- **Stock Commands**: `/stock AAPL` - Get real-time stock prices
- **Help System**: `/help` - List available commands
- **Serverless Architecture**: Auto-scaling Cloud Functions
- **Real-time Processing**: Pub/Sub message queuing
- **Data Storage**: Firestore for user data and analytics

## Architecture

```
Signal → Webhook → Pub/Sub → Message Processor → Stock Handler → Response
```

**GCP Services Used:**
- Cloud Functions (Python 3.11)
- Pub/Sub for message queuing
- Firestore for data storage
- Secret Manager for API keys
- Cloud Storage for function code

## Quick Start

### Prerequisites

- Google Cloud account with billing enabled
- `gcloud` CLI installed and authenticated
- `terraform` installed
- Signal API access (signal-api or similar)

### Deployment

1. **Clone and configure**:
```bash
git clone <repository>
cd signalbot
```

2. **Set your project ID**:
```bash
export PROJECT_ID="your-gcp-project-id"
```

3. **Deploy infrastructure**:
```bash
chmod +x deploy/deploy.sh
./deploy/deploy.sh $PROJECT_ID
```

4. **Configure Signal API secrets**:
```bash
# Set your Signal API URL
gcloud secrets versions add signal-api-url --data-file=- <<< 'https://your-signal-api-url'

# Set your Signal API token
gcloud secrets versions add signal-api-token --data-file=- <<< 'your-signal-api-token'
```

5. **Configure Signal webhook**:
   - Use the webhook URL from deployment output
   - Point your Signal API to: `https://your-region-your-project.cloudfunctions.net/signal-webhook`

## Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/stock <ticker>` | Get current stock price | `/stock AAPL` |
| `/help` | Show available commands | `/help` |

## Project Structure

```
signalbot/
├── functions/
│   ├── webhook/           # Signal webhook handler
│   ├── message-processor/ # Command parsing and routing
│   └── stock-handler/     # Stock data fetching
├── shared/               # Common utilities
├── terraform/           # Infrastructure as Code
├── deploy/             # Deployment scripts
└── README.md
```

## Configuration

### Environment Variables

Set in Cloud Function configurations:
- `GOOGLE_CLOUD_PROJECT`: Your GCP project ID
- `GCP_REGION`: Deployment region

### Secrets (Secret Manager)

- `signal-api-url`: Your Signal API endpoint
- `signal-api-token`: Signal API authentication token

## Monitoring

- **Logs**: Cloud Logging
- **Metrics**: Cloud Monitoring
- **Traces**: Cloud Trace

View logs:
```bash
gcloud functions logs read signal-webhook
gcloud functions logs read message-processor
gcloud functions logs read stock-handler
```

## Development

### Local Testing

1. Install dependencies:
```bash
pip install -r functions/webhook/requirements.txt
```

2. Set environment variables:
```bash
export GOOGLE_CLOUD_PROJECT="your-project"
```

3. Run functions locally:
```bash
functions-framework --target=signal_webhook --port=8080
```

### Adding Commands

1. Create new handler in `functions/`
2. Add routing logic in `message-processor`
3. Update help text
4. Deploy updates

## Cost Optimization

- Functions scale to zero when idle
- Pub/Sub pricing is per message
- Firestore pricing is per read/write
- Estimated cost: $1-5/month for moderate usage

## Troubleshooting

### Common Issues

1. **Permission Errors**: Ensure service account has required IAM roles
2. **Secret Access**: Verify Secret Manager permissions
3. **Pub/Sub Issues**: Check topic and subscription configurations

### Debug Commands

```bash
# Check function status
gcloud functions describe signal-webhook --region=us-central1

# View recent logs
gcloud functions logs read signal-webhook --limit=50

# Test webhook locally
curl -X POST -H "Content-Type: application/json" -d '{"test": "message"}' http://localhost:8080
```

## Security

- API keys stored in Secret Manager
- Service accounts with minimal permissions
- HTTPS-only endpoints
- Input validation and sanitization

## Contributing

1. Fork the repository
2. Create a feature branch
3. Test changes locally
4. Submit a pull request

## License

MIT License - see LICENSE file for details