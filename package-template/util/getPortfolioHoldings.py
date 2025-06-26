import os
import requests
import json
import logging

# --- Constants and Path Setup ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "..", "configs", "config.json")
AUTH_TOKEN_PATH = os.path.join(BASE_DIR, "..", "files", "auth_token.txt")
HOLDING_PATH = os.path.join(BASE_DIR, "..", "files", "holding.json")

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

def load_config():
    """Load configuration from JSON file."""
    try:
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Configuration file not found at {CONFIG_PATH}")
        raise
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from {CONFIG_PATH}")
        raise

def get_portfolio_holdings():
    """
    Fetches portfolio holdings from the IIFL API and saves them to a file.
    """
    logger.info("Starting to fetch portfolio holdings...")

    # 1. Load configuration to get API endpoint
    try:
        config = load_config()
        base_url = config.get("IIFL_BASE_URL")
        endpoint = config.get("HOLDINGS_ENDPOINT")
        if not base_url or not endpoint:
            msg = "API URL or holdings endpoint not found in config.json"
            logger.error(msg)
            return False, msg
        url = base_url + endpoint
    except Exception as e:
        return False, f"Failed to load configuration: {e}"

    # 2. Read the authentication token
    try:
        logger.debug(f"Reading auth token from {AUTH_TOKEN_PATH}")
        with open(AUTH_TOKEN_PATH, "r") as f:
            token = f.read().strip()
        if not token:
            return False, "Auth token file is empty."
        logger.info("Successfully read auth token.")
    except FileNotFoundError:
        logger.error(f"Auth token file not found at: {AUTH_TOKEN_PATH}")
        return False, "Auth token file not found. Please get a session first."
    except IOError as e:
        logger.error(f"Failed to read auth token: {e}")
        return False, "Failed to read auth token"

    # 3. Make the API request
    headers = {"Authorization": f"Bearer {token}"}
    try:
        logger.info(f"Sending GET request to {url}")
        response = requests.get(url, headers=headers, timeout=30)
        logger.info(f"Received response with status code: {response.status_code}")
        response.raise_for_status()
        holdings_data = response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error while fetching Portfolio Holdings: {e}")
        return False, f"API error while fetching holdings: {e}"

    # 4. Save the holdings data to a file
    try:
        os.makedirs(os.path.dirname(HOLDING_PATH), exist_ok=True)
        with open(HOLDING_PATH, "w") as f:
            json.dump(holdings_data, f, indent=2)
        logger.info(f"Portfolio holdings saved to {HOLDING_PATH}")
        return True, "Portfolio holdings fetched and saved successfully."
    except (IOError, TypeError) as e:
        logger.error(f"Error while saving Portfolio Holdings: {e}")
        return False, "Error while saving portfolio holdings to file."

if __name__ == "__main__":
    success, message = get_portfolio_holdings()
    print(f"Success: {success}, Message: {message}")