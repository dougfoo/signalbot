import json
import logging
import base64
import yfinance as yf
from google.cloud import secretmanager
import functions_framework
import os
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Secret Manager client
secret_client = secretmanager.SecretManagerServiceClient()
project_id = os.environ.get('GOOGLE_CLOUD_PROJECT')

@functions_framework.cloud_event
def handle_stock_request(cloud_event):
    """
    Cloud Function to handle stock data requests.
    Fetches stock data and sends formatted response.
    """
    try:
        # Decode Pub/Sub message
        pubsub_message = base64.b64decode(cloud_event.data["message"]["data"])
        request_data = json.loads(pubsub_message.decode('utf-8'))

        logger.info(f"Processing stock request: {request_data}")

        # Extract request details
        sender = request_data.get('sender')
        ticker = request_data.get('ticker')
        group_id = request_data.get('group_id')

        # Fetch stock data
        stock_info = get_stock_data(ticker)

        if stock_info['success']:
            message = format_stock_message(ticker, stock_info['data'])
        else:
            message = f"❌ Error fetching data for {ticker}: {stock_info['error']}"

        # Send response (integrate with Signal API)
        send_signal_response(sender, message, group_id)

    except Exception as e:
        logger.error(f"Error handling stock request: {str(e)}")

def get_stock_data(ticker):
    """Fetch stock data using yfinance"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="1d")

        if hist.empty:
            return {'success': False, 'error': 'No data found for ticker'}

        current_price = hist['Close'].iloc[-1]
        prev_close = info.get('previousClose', current_price)
        change = current_price - prev_close
        change_percent = (change / prev_close) * 100 if prev_close else 0

        return {
            'success': True,
            'data': {
                'symbol': ticker,
                'name': info.get('longName', ticker),
                'price': current_price,
                'change': change,
                'change_percent': change_percent,
                'volume': hist['Volume'].iloc[-1] if not hist['Volume'].empty else 0,
                'market_cap': info.get('marketCap'),
                'pe_ratio': info.get('forwardPE')
            }
        }

    except Exception as e:
        logger.error(f"Error fetching stock data for {ticker}: {str(e)}")
        return {'success': False, 'error': str(e)}

def format_stock_message(ticker, data):
    """Format stock data into a readable message"""
    change_emoji = "🟢" if data['change'] >= 0 else "🔴"
    change_sign = "+" if data['change'] >= 0 else ""

    message = f"""📈 {data['name']} ({data['symbol']})

💰 Price: ${data['price']:.2f}
{change_emoji} Change: {change_sign}${data['change']:.2f} ({change_sign}{data['change_percent']:.2f}%)
📊 Volume: {data['volume']:,}"""

    if data.get('market_cap'):
        market_cap_b = data['market_cap'] / 1e9
        message += f"\n🏢 Market Cap: ${market_cap_b:.1f}B"

    if data.get('pe_ratio'):
        message += f"\n📊 P/E Ratio: {data['pe_ratio']:.2f}"

    message += f"\n\n⏰ Updated: {datetime.now().strftime('%H:%M:%S UTC')}"

    return message

def send_signal_response(sender, message, group_id):
    """Send response back to Signal"""
    # TODO: Implement Signal API integration
    # This would use Signal's API to send the formatted message back
    logger.info(f"Sending stock response to {sender} (group: {group_id}): {message}")

    # Placeholder for Signal API call
    # signal_api.send_message(
    #     recipient=sender,
    #     message=message,
    #     group_id=group_id
    # )