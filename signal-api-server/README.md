# Signal API Server Setup

This directory contains the setup for deploying signal-api to a cloud server.

## Option B: Cloud Server Deployment

### Cloud Platforms

**1. DigitalOcean (Recommended - $5/month)**
```bash
# Create a Droplet with Docker pre-installed
# SSH into your server
ssh root@your-server-ip

# Clone and deploy
git clone https://github.com/dougfoo/signalbot.git
cd signalbot/signal-api-server
docker-compose up -d
```

**2. AWS EC2**
```bash
# Launch t3.micro instance with Ubuntu
# Install Docker and Docker Compose
sudo apt update
sudo apt install docker.io docker-compose -y
sudo systemctl start docker
sudo systemctl enable docker

# Deploy signal-api
git clone https://github.com/dougfoo/signalbot.git
cd signalbot/signal-api-server
sudo docker-compose up -d
```

**3. Google Cloud VM**
```bash
# Create Compute Engine instance
gcloud compute instances create signal-api-server \
  --zone=us-central1-a \
  --machine-type=e2-micro \
  --image-family=ubuntu-2004-lts \
  --image-project=ubuntu-os-cloud \
  --tags=http-server

# SSH and setup
gcloud compute ssh signal-api-server
sudo apt update && sudo apt install docker.io docker-compose -y
# Clone and deploy as above
```

### After Deployment

1. **Open firewall for port 8080**
2. **Register your phone number**:
```bash
curl -X POST http://your-server-ip:8080/v1/register/+81804142-7606
```
3. **Verify with SMS code**:
```bash
curl -X POST http://your-server-ip:8080/v1/register/+81804142-7606/verify/SMS_CODE
```

### Configuration

The docker-compose.yml is pre-configured to:
- Run signal-api on port 8080
- Auto-receive messages every 10 seconds
- Forward messages to your GCP webhook
- Persist Signal data between restarts

## Quick Start Commands

```bash
# Start the service
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the service
docker-compose down

# Register phone number
curl -X POST http://localhost:8080/v1/register/+81804142-7606

# Send test message
curl -X POST http://localhost:8080/v1/send \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello from Signal bot!",
    "number": "+81804142-7606",
    "recipients": ["+81804142-7606"]
  }'
```