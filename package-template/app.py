from flask import Flask, render_template, request, send_from_directory, redirect, url_for
import os
import logging
import subprocess
import json
from util.getUserSession import get_user_session_wrapper
from util.getPortfolioHoldings import get_portfolio_holdings
from util.fetch_candle_stick_data import fetch_candle_stick_data # Ensure this file exists
from util.calculate_atr import calculate_atr

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Needed for session

# Setup logger
log_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'log')
os.makedirs(log_dir, exist_ok=True)
log_path = os.path.join(log_dir, 'app.log')
logging.basicConfig(
    filename=log_path,
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

def getUserSession(auth_code):
    logger.info(f"getUserSession called with auth_code: {auth_code}")
    auth_token = get_user_session_wrapper(auth_code)
    if auth_token:
        return True, "Session details fetched successfully"
    else:
        return False, "Failed to fetch session details"

def fetch_candle_stick_data_wrapper():
    success, message = fetch_candle_stick_data()
    return success, message

def calculate_atr_wrapper():
    success, message = calculate_atr()
    return success, message

@app.route('/clean_project', methods=['POST'])
def clean_project():
    try:
        logger.info("Running clean_project.py...")
        result = subprocess.run(['python', 'util/clean_project.py'], capture_output=True, text=True, check=True)
        logger.info(f"clean_project.py output: {result.stdout}")
        feedback = "Project cleaned successfully."
    except subprocess.CalledProcessError as e:
        feedback = f"Cleanup error: {e.stdout or e.stderr}"
        logger.error(f"Cleanup error: {e.stdout or e.stderr}")
    except Exception as e:
        feedback = f"Unexpected cleanup error: {str(e)}"
        logger.exception("Exception during cleanup:")
    
    return redirect(url_for('index', feedback=feedback))

def get_auth_code_from_config():
    """Reads auth_code from config.json to pre-fill the form."""
    config_path = os.path.join(os.path.dirname(__file__), 'files', 'config.json')
    if not os.path.exists(config_path):
        return ''
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            return config.get('auth_code', '')
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error reading auth_code from {config_path}: {e}")
        return ''

@app.route('/', methods=['GET', 'POST'])
def index():
    feedback = request.args.get('feedback', '')
    show_report = False
    auth_code_value = get_auth_code_from_config()
    try:
        if request.method == 'POST':
            # Step 1: Get User Session
            auth_code = request.form.get('auth_code', '')
            logger.info(f"Received auth_code from user: {auth_code}")
            ok, msg = getUserSession(auth_code)
            if not ok:
                feedback = f"Session error: {msg}"
                logger.error(feedback)
                # Render template and stop if session fails
                return render_template('main.html', feedback=feedback, show_report=show_report, auth_code_value=auth_code_value)
            
            feedback = f"Session successful. {msg}"
            logger.info("Session step successful.")

            # Step 2: Get Portfolio Holdings
            logger.info("Fetching portfolio holdings...")
            ok, msg = get_portfolio_holdings()
            if not ok:
                feedback = f"Holdings error: {msg}"
                logger.error(feedback)
                return render_template('main.html', feedback=feedback, show_report=show_report, auth_code_value=auth_code_value)
            logger.info("Holdings step successful.")
            feedback = f"Holdings fetched successfully. {msg}"

            # Step 3: Fetch Candle Stick Data
            logger.info("Fetching candle stick data...")
            ok, msg = fetch_candle_stick_data_wrapper()
            if not ok:
                feedback = f"Candle data error: {msg}"
                logger.error(feedback)
                return render_template('main.html', feedback=feedback, show_report=show_report, auth_code_value=auth_code_value)
            logger.info("Candle stick data step successful.")
            feedback = f"Candle data fetched. {msg}"

            # Step 4: Calculate ATR
            logger.info("Calculating ATR...")
            ok, msg = calculate_atr_wrapper()
            if not ok:
                feedback = f"ATR calculation error: {msg}"
                logger.error(feedback)
            else:
                logger.info("ATR calculation step successful.")
                feedback = f"All steps successful. {msg}"
                show_report = True

    except Exception as e:
        feedback = f"Unexpected error: {str(e)}"
        logger.exception("Exception in main workflow:")
    return render_template('main.html', feedback=feedback, show_report=show_report, auth_code_value=auth_code_value)

@app.route('/report')
def report():
    """Serves the generated ATR report file."""
    report_path = os.path.join(os.path.dirname(__file__), 'files')
    return send_from_directory(report_path, 'atr.json')

if __name__ == '__main__':
    app.run(debug=True)