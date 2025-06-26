import json
import os
import hashlib
import requests
import logging
import datetime

# --- Constants and Path Setup ---
# Construct absolute paths from the script's location to avoid relative path issues.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "..", "configs", "config.json")
AUTH_TOKEN_PATH = os.path.join(BASE_DIR, "..", "files", "auth_token.txt")
SESSION_KEY = "userSession"  # Key to look for in the API response

# --- Logging Setup ---
logger = logging.getLogger(__name__)

def setup_logging():
    # Configure logging to a central log file.
    # This setup is guarded to prevent adding duplicate handlers if imported elsewhere.
    log_dir = os.path.join(BASE_DIR, '..', 'log')
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, 'app.log')
    
    if not logger.handlers:
        # Use a file handler to log messages.
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(logging.DEBUG)
        # Define a standard format for log messages.
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.setLevel(logging.DEBUG)

# Initialize logging when the module is loaded.
setup_logging()

def load_config():
    """Load configuration from JSON file."""
    try:
        logger.debug(f"Loading config from {CONFIG_PATH}")
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Configuration file not found at {CONFIG_PATH}")
        raise
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from {CONFIG_PATH}")
        raise
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        raise

def save_config(config):
    """Save configuration to JSON file."""
    try:
        logger.debug(f"Saving config to {CONFIG_PATH}")
        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=2)
        logger.info(f"Config saved successfully to {CONFIG_PATH}")
    except Exception as e:
        logger.error(f"Failed to save config: {e}")
        raise

def get_user_session(config, auth_code):
    """Request a new user session from the IIFL API."""
    # Construct the checksum required by the API.
    checksum_str = config.get("ClientId", "") + auth_code + config.get("AppSecret", "")
    checksum = sha256_hash(checksum_str)

    url = config.get("IIFL_BASE_URL", "") + config.get("GET_USER_SESSION_ENDPOINT", "")
    headers = {"Content-Type": "application/json"}
    # The payload for the session request includes the checksum.
    payload = {
        "checkSum": checksum
    }
    
    logger.debug(f"Requesting user session. URL: {url}")
    logger.debug(f"Request payload: {payload}")
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
        logger.info(f"Session request response status: {response.status_code}")
        logger.debug(f"Session response text: {response.text}")
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error during API request for user session: {e}")
        return {}

def sha256_hash(input_string: str) -> str:
    """Returns the SHA-256 hash of the input string."""
    return hashlib.sha256(input_string.encode('utf-8')).hexdigest()

def is_auth_file_valid():
    """
    Check if the auth token file exists, is not empty, and was created today.
    This prevents re-authentication if a valid token from the same day already exists.
    """
    if not os.path.exists(AUTH_TOKEN_PATH):
        logger.debug(f"Auth file {AUTH_TOKEN_PATH} does not exist.")
        return False
        
    # Check if the file was created today.
    mtime = os.path.getmtime(AUTH_TOKEN_PATH)
    file_date = datetime.datetime.fromtimestamp(mtime).date()
    if file_date != datetime.datetime.now().date():
        logger.info(f"Auth file {AUTH_TOKEN_PATH} is stale (not from today). A new token is required.")
        return False
        
    try:
        # Check if the file contains a token.
        with open(AUTH_TOKEN_PATH, "r") as f:
            token = f.read().strip()
            if token:
                logger.info(f"Valid auth token found in {AUTH_TOKEN_PATH} from today.")
                return True
            else:
                logger.debug(f"Auth file {AUTH_TOKEN_PATH} is empty.")
                return False
    except IOError as e:
        logger.error(f"Error reading auth token file {AUTH_TOKEN_PATH}: {e}")
        return False

def save_auth_token(token):
    """Save the auth token to a file."""
    try:
        # Ensure the directory exists.
        os.makedirs(os.path.dirname(AUTH_TOKEN_PATH), exist_ok=True)
        with open(AUTH_TOKEN_PATH, "w") as f:
            f.write(token)
        logger.info(f"Auth token saved successfully to {AUTH_TOKEN_PATH}")
    except IOError as e:
        logger.error(f"Failed to write auth token to {AUTH_TOKEN_PATH}: {e}")

def get_user_session_wrapper(auth_code_from_user=None):
    """
    Main wrapper to handle the user session process.
    It checks for an existing valid token first. If not found or expired,
    it uses the provided auth_code to fetch a new one.
    """
    logger.info("Starting get_user_session_wrapper...")
    
    # 1. Check for an existing, valid auth token from today.
    if is_auth_file_valid():
        try:
            with open(AUTH_TOKEN_PATH, "r") as f:
                auth_token = f.read().strip()
            logger.info("Using existing valid auth token from file.")
            return auth_token
        except IOError as e:
            logger.error(f"Could not read existing auth token file despite validation: {e}")
            # Proceed to fetch a new token.

    logger.info("No valid auth token file found. Attempting to fetch a new session.")
    
    try:
        config = load_config()
    except Exception:
        # If config fails to load, we cannot proceed.
        return None

    # 2. Determine which auth code to use.
    # The one from the user (e.g., web form) takes precedence.
    auth_code_to_use = auth_code_from_user or config.get("AuthCode")
    
    if not auth_code_to_use:
        logger.error("No auth code provided and none found in config. Cannot get session.")
        return None

    # If a new auth code is provided by the user, update the config for command-line convenience.
    if auth_code_from_user and auth_code_from_user != config.get("AuthCode"):
        logger.info("New auth code provided by user. Updating config for future command-line use.")
        config["AuthCode"] = auth_code_from_user
        save_config(config)

    # 3. Fetch a new session from the API.
    session_data = get_user_session(config, auth_code_to_use)
    auth_token = session_data.get(SESSION_KEY)
    
    # 4. Save the new token if successfully retrieved.
    if auth_token:
        save_auth_token(auth_token)
        logger.info("Successfully fetched and saved new auth token.")
    else:
        logger.warning("Failed to retrieve auth token from session response.")
        logger.debug(f"Full session response: {session_data}")
    
    return auth_token

if __name__ == "__main__":
    import sys
    # Allows running the script from the command line with an auth code.
    # e.g., python util/getUserSession.py YOUR_AUTH_CODE
    if len(sys.argv) > 1:
        new_auth_code = sys.argv[1]
        print(f"Attempting to get session with auth code: {new_auth_code}")
        token = get_user_session_wrapper(new_auth_code)
        if token:
            print("Successfully retrieved and saved auth token.")
        else:
            print("Failed to retrieve auth token.")
    else:
        print("Usage: python util/getUserSession.py <auth_code>")