import numpy as np
if not hasattr(np, "NaN"):
    np.NaN = np.nan

import os
import json
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import logging

try:
    # For Python 3.8+ use importlib.metadata
    from importlib.metadata import version as get_distribution, PackageNotFoundError as DistributionNotFound
except ImportError:
    # Fall back to pkg_resources (deprecated)
    from pkg_resources import get_distribution, DistributionNotFound

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

def load_holdings(holdings_file):
    """Load holdings from a JSON file."""
    try:
        with open(holdings_file, "r") as f:
            data = json.load(f)
        logger.info(f"Successfully loaded holdings from {holdings_file}")
        return data
    except Exception as e:
        logger.error("Error loading holdings file")
        raise

def calculate_indicators(ticker, period='1y'):
    """Fetch historical data for the ticker and calculate technical indicators."""
    logger.info(f"Fetching data for {ticker}")
    logger.debug(f"About to download data for ticker: {ticker} for period: {period}")
    try:
        data = yf.download(ticker, period=period)
    except Exception as e:
        if "No data found" in str(e):
            logger.warning(f"No data found for ticker {ticker} (possibly delisted).")
        else:
            logger.error(f"Error fetching data for {ticker}: {e}")
        return None

    if data.empty:
        logger.warning(f"No data found for ticker {ticker} (possibly delisted; Yahoo error: 'No data found, symbol may be delisted')")
        return None

    logger.debug(f"Downloaded columns for {ticker}: {data.columns.to_list()}")
    logger.debug(f"Downloaded data for {ticker} (head):\n{data.head().to_string()}")
    logger.debug(f"Downloaded data for {ticker} (tail):\n{data.tail().to_string()}")

    if 'Close' not in data.columns:
        logger.error(f"Downloaded data for ticker {ticker} is missing the 'Close' column.")
        return None

    df = data.copy()

    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    logger.debug(f"SMA_20 for {ticker} (tail):\n{df['SMA_20'].tail().to_string()}")

    df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
    logger.debug(f"EMA_20 for {ticker} (tail):\n{df['EMA_20'].tail().to_string()}")

    df['RSI'] = ta.rsi(df['Close'], length=14)
    logger.debug(f"RSI for {ticker} (tail):\n{df['RSI'].tail().to_string()}")

    macd = ta.macd(df['Close'])
    if macd is None or 'MACD_12_26_9' not in macd:
        logger.error(f"MACD calculation failed for ticker {ticker}.")
        return None

    # Now it's safe to log MACD details.
    logger.debug(f"MACD output for {ticker} (head):\n{macd.head().to_string()}")
    df['MACD'] = macd['MACD_12_26_9']
    df['MACD_Signal'] = macd['MACDs_12_26_9']
    logger.debug(f"MACD for {ticker} (tail):\n{df['MACD'].tail().to_string()}")
    logger.debug(f"MACD_Signal for {ticker} (tail):\n{df['MACD_Signal'].tail().to_string()}")

    return df

def main():
    holdings_file = os.path.join(os.path.dirname(__file__), "../files/holding.json")
    if not os.path.exists(holdings_file):
        logger.error(f"Holdings file not found at {holdings_file}")
        return

    # Load full JSON data.
    data = load_holdings(holdings_file)
    # Extract holdings from the "result" key if available.
    holdings = data["result"] if "result" in data else data

    for holding in holdings:
        # Log the entire holding for debugging.
        logger.debug(f"Processing holding: {holding}")

        if isinstance(holding, dict):
            # Prefer NSE ticker if available.
            if "nseTradingSymbol" in holding and isinstance(holding["nseTradingSymbol"], str):
                # Remove any "-EQ" part and append the NSE suffix.
                ticker = holding["nseTradingSymbol"].replace("-EQ", "").strip() + ".NS"
            elif "bseTradingSymbol" in holding and isinstance(holding["bseTradingSymbol"], str):
                ticker = holding["bseTradingSymbol"].strip() + ".BO"
            else:
                logger.warning(f"Skipping holding (no valid ticker found): {holding}")
                continue
        else:
            # In case the holding is not a dict, assume it is a ticker string.
            ticker = holding

        # Additional check: ignore unwanted placeholders.
        if not ticker or ticker.lower() in ["status", "result"]:
            logger.warning(f"Skipping holding due to invalid ticker value: {ticker}")
            continue

        logger.info(f"Using ticker: {ticker}")
        df = calculate_indicators(ticker)
        if df is not None:
            indicators = df[['SMA_20', 'EMA_20', 'RSI', 'MACD', 'MACD_Signal']].tail()
            logger.info(f"Indicators for {ticker}: \n{indicators}\n")
        else:
            logger.warning(f"Could not calculate indicators for {ticker}")

if __name__ == "__main__":
    main()