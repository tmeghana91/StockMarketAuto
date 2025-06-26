import os
import json
import requests
import logging
from datetime import datetime, timedelta

# --- Constants and Path Setup ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "..", "configs", "config.json")
AUTH_TOKEN_PATH = os.path.join(BASE_DIR, "..", "files", "auth_token.txt")
HOLDING_PATH = os.path.join(BASE_DIR, "..", "files", "holding.json") # This path remains in files
NSEEQ_PATH = os.path.join(BASE_DIR, "..", "static", "NSEEQ.json") # Updated path to static

# --- Logging Setup ---
logger = logging.getLogger(__name__)

def setup_logging():
    """Configure logging for the module."""
    log_dir = os.path.join(BASE_DIR, '..', 'log')
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, 'app.log')
    if not logger.handlers:
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.setLevel(logging.DEBUG)

setup_logging()

def load_json_file(file_path, description):
    """Generic function to load a JSON file with proper error handling."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"{description} file not found at: {file_path}")
        raise
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from {description} file: {file_path}")
        raise

def get_instrument_id_map():
    """Loads NSEEQ.json and creates a mapping from trading symbol to instrumentId."""
    try:
        contracts = load_json_file(NSEEQ_PATH, "NSE contracts")
        id_map = {c['tradingSymbol']: c.get('instrumentId') for c in contracts if c.get('tradingSymbol') and c.get('exchange') == 'NSEEQ'}
        logger.info(f"Created instrument ID map with {len(id_map)} entries.")
        return id_map
    except Exception as e:
        logger.error(f"Failed to create instrument ID map: {e}")
        return {}

def fetch_candle_stick_data():
    """Fetches historical candle data for each holding and updates the holding file."""
    logger.info("Starting to fetch candle stick data for holdings...")
    try:
        config = load_json_file(CONFIG_PATH, "Config")
        holdings_data = load_json_file(HOLDING_PATH, "Holdings")
        instrument_id_map = get_instrument_id_map()
        
        with open(AUTH_TOKEN_PATH, 'r') as f:
            token = f.read().strip()
        if not token:
            return False, "Auth token is missing or empty."

    except Exception as e:
        return False, f"Failed during initial setup: {e}"

    base_url = config.get("IIFL_BASE_URL")
    endpoint = config.get("HISTORICAL_DATA_ENDPOINT")
    if not base_url or not endpoint:
        return False, "Historical data API URL or endpoint not found in config."
    
    url = base_url + endpoint
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    holdings = holdings_data.get("result", [])
    if not isinstance(holdings, list):
        return False, "Holdings data is not in the expected list format."

    # Define periods for percentage change calculations (approximate trading days)
    periods = {
        "1w": 5,
        "14d": 10, # Changed from 14 to 10 for more accurate trading days in 2 weeks
        "1m": 21,
        "3m": 63,
        "6m": 126,
        "1y": 252,
        "3y": 756
    }

    to_date = datetime.now()
    from_date = to_date - timedelta(days=3*365 + 90) # ~3 years and 3 months of calendar days
    to_date_str, from_date_str = to_date.strftime("%d-%b-%Y").lower(), from_date.strftime("%d-%b-%Y").lower()

    for holding in holdings:
        trading_symbol = holding.get("nseTradingSymbol")
        if not trading_symbol or not (instrument_id := instrument_id_map.get(trading_symbol)):
            logger.warning(f"Skipping holding due to missing symbol or instrumentId: {holding.get('bseTradingSymbol', 'N/A')}")
            continue
            
        payload = {"exchange": "NSEEQ", "instrumentId": str(instrument_id), "interval": "1 day", "fromDate": from_date_str, "toDate": to_date_str}
        
        try:
            logger.debug(f"Fetching data for {trading_symbol} (ID: {instrument_id})")
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            candles_raw = response.json().get("result", [{}])[0].get("candles", []) # Candles are [timestamp, open, high, low, close, volume]
            formatted_candles = [{"high": c[2], "low": c[3], "close": c[4]} for c in candles_raw if len(c) >= 5]
            
            holding["historical_data"] = formatted_candles # Store all fetched candles
            if formatted_candles:
                holding["last_close"] = formatted_candles[-1]['close']
                # Calculate highest price within the fetched period
                holding["highest_price_in_period"] = max(c['high'] for c in formatted_candles)
            else:
                holding["last_close"] = holding.get("previousDayClose", 0) # Fallback
                holding["highest_price_in_period"] = holding.get("previousDayClose", 0) # Fallback

            holding["purchase_price"] = holding.get("averageTradedPrice", 0)

            # Calculate percentage changes for various periods
            holding["percentage_changes"] = {}
            current_close = holding["last_close"]

            for label, days_count in periods.items():
                if len(formatted_candles) > days_count:
                    past_close = formatted_candles[-days_count-1]['close'] # -1 for 0-indexed, -1 for previous day
                    if past_close != 0:
                        pct_change = ((current_close - past_close) / past_close) * 100
                        holding["percentage_changes"][label] = round(pct_change, 2)
                    else:
                        holding["percentage_changes"][label] = None # Avoid division by zero
                else:
                    holding["percentage_changes"][label] = None # Not enough data

            logger.info(f"Successfully fetched {len(formatted_candles)} candles for {trading_symbol}. Calculated percentage changes: {holding['percentage_changes']}")

        except requests.exceptions.RequestException as e:
            logger.error(f"API error fetching data for {trading_symbol}: {e}")
            holding["historical_data"] = [] # Clear data on error
            holding["percentage_changes"] = {} # Clear changes on error
            holding["highest_price_in_period"] = holding.get("previousDayClose", 0) # Fallback
        except Exception as e:
            logger.error(f"Unexpected error processing {trading_symbol} candle data: {e}")
            holding["historical_data"] = []
            holding["percentage_changes"] = {}
            holding["highest_price_in_period"] = holding.get("previousDayClose", 0) # Fallback

    try:
        with open(HOLDING_PATH, 'w', encoding='utf-8') as f:
            json.dump(holdings_data, f, indent=2)
        logger.info(f"Updated holdings data with candle information and percentage changes saved to {HOLDING_PATH}")
        return True, "Successfully fetched candle stick data and calculated percentage changes."
    except IOError as e:
        logger.error(f"Failed to save updated holdings file: {e}")
        return False, "Failed to save updated holdings file."

if __name__ == "__main__":
    success, message = fetch_candle_stick_data()
    print(f"Success: {success}, Message: {message}")
    