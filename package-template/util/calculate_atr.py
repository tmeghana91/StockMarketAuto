import json
import os # Keep os for path operations
import pandas as pd
import numpy as np
import logging

# --- Configuration ---
ATR_PERIOD = 14                  # Number of days to calculate ATR
ATR_MULTIPLIER = 2.5             # Multiplier for trailing stop loss

# --- Path Setup ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HOLDINGS_FILE = os.path.join(BASE_DIR, "..", "files", "holding.json")
OUTPUT_FILE = os.path.join(BASE_DIR, "..", "files", "atr.json")

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

def _calculate_atr_for_df(high_prices, low_prices, close_prices, period):
    """
    Internal function to calculate ATR from pandas Series.
    """
    df = pd.DataFrame({
        'high': high_prices,
        'low': low_prices,
        'close': close_prices
    })
    
    # Calculate True Range (TR)
    df['tr1'] = df['high'] - df['low']
    df['tr2'] = (df['high'] - df['close'].shift(1)).abs()
    df['tr3'] = (df['low'] - df['close'].shift(1)).abs()
    df['true_range'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
    
    # Calculate ATR using a simple rolling mean
    atr_values = df['true_range'].rolling(window=period).mean()
    return atr_values.iloc[-1] if not atr_values.empty and pd.notna(atr_values.iloc[-1]) else 0

def calculate_atr():
    """
    Loads holdings, calculates ATR and trailing stop loss for each, and saves the result.
    """
    logger.info("Starting ATR calculation process...")
    try:
        with open(HOLDINGS_FILE, 'r', encoding='utf-8') as f:
            holdings_data = json.load(f)
    except FileNotFoundError:
        msg = f"Holdings file not found: {HOLDINGS_FILE}"
        logger.error(msg)
        return False, msg
    except json.JSONDecodeError as e:
        msg = f"Error decoding holdings JSON: {e}"
        logger.error(msg)
        return False, msg

    holdings = holdings_data.get("result", [])
    if not isinstance(holdings, list):
        msg = "Holdings data is not in the expected list format."
        logger.error(msg)
        return False, msg

    processed_count = 0
    for holding in holdings:
        symbol = holding.get("bseTradingSymbol") or holding.get("nseTradingSymbol", "Unknown")
        
        # Check for required fields, now using 'historical_data' and 'highest_price_in_period'
        if not all(k in holding for k in ["purchase_price", "highest_price_in_period", "historical_data"]):
            logger.warning(f"Skipping {symbol}: missing required data (purchase_price, highest_price_in_period, or historical_data).")
            continue
        
        candle_data = holding["historical_data"] # Use the full historical data
        if not candle_data or len(candle_data) < ATR_PERIOD:
            logger.warning(f"Skipping {symbol}: not enough candle data ({len(candle_data)} days) for ATR-{ATR_PERIOD}.")
            holding["atr_value"], holding["trailing_stop_loss"], holding["action"] = 0, holding["purchase_price"], "HOLD"
            continue

        df = pd.DataFrame(candle_data)
        for col in ['high', 'low', 'close']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        df.dropna(inplace=True)
        # Ensure enough data points after dropping NaNs for ATR calculation
        if len(df) < ATR_PERIOD:
            logger.warning(f"Skipping {symbol}: not enough valid candle data ({len(df)} days after cleanup) for ATR-{ATR_PERIOD}.")
            holding["atr_value"], holding["trailing_stop_loss"], holding["action"] = 0, holding["purchase_price"], "HOLD"
            continue

        atr_value = _calculate_atr_for_df(df['high'], df['low'], df['close'], ATR_PERIOD)
        
        holding["atr_value"] = atr_value
        
        trailing_sl = holding["highest_price_in_period"] - (atr_value * ATR_MULTIPLIER)
        trailing_sl = max(holding["purchase_price"], trailing_sl)
        holding["trailing_stop_loss"] = trailing_sl
        
        current_price = df['close'].iloc[-1] if not df.empty else holding.get("last_close", holding["purchase_price"])
        
        holding["action"] = "SELL" if current_price <= trailing_sl else "HOLD"
        logger.debug(f"{symbol}: ATR={atr_value:.2f}, TSL={trailing_sl:.2f}, Action={holding['action']}")
        processed_count += 1
    
    try:
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f_out:
            json.dump(holdings, f_out, indent=4) # Dump the list of holdings directly
        msg = f"ATR report ready. Processed {processed_count}/{len(holdings)} holdings."
        logger.info(msg)
        return True, msg
    except IOError as e:
        msg = f"Failed to save ATR report: {e}"
        logger.error(msg)
        return False, msg

if __name__ == "__main__":
    success, message = calculate_atr()
    print(f"Success: {success}, Message: {message}")