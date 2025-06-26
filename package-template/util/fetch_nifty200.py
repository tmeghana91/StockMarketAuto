import requests
import pandas as pd
import json
import os
import logging
import yfinance as yf
from datetime import datetime, timedelta

# Setup logging to D:\Py_code\Stock_Trading_Auto\log
log_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..', 'log')
os.makedirs(log_dir, exist_ok=True)
log_path = os.path.join(log_dir, 'fetch_nifty200.log')
logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

csv_url = "https://www1.nseindia.com/content/indices/ind_nifty200list.csv"
output_path = os.path.join("files", "nifty200.json")

logger.info("Starting download of Nifty 200 CSV from NSE...")
try:
    response = requests.get(csv_url)
    response.raise_for_status()
    logger.info("CSV downloaded successfully.")
except Exception as e:
    logger.error(f"Failed to download CSV: {e}")
    raise

try:
    df = pd.read_csv(pd.compat.StringIO(response.text))
    logger.info(f"CSV parsed. Columns: {list(df.columns)}")
    symbols = df['Symbol'].tolist()
    logger.info(f"Extracted {len(symbols)} symbols from CSV.")
except Exception as e:
    logger.error(f"Failed to parse CSV or extract symbols: {e}")
    raise

# Periods to calculate change for (in days)
periods = {
    'change_1w': 5,
    'change_14d': 14,
    'change_30d': 30,
    'change_3m': 63,   # ~21 trading days/month
    'change_6m': 126,
    'change_1y': 252,
    'change_2y': 504,
    'change_3y': 756
}

results = []
now = datetime.now()

for symbol in symbols:
    yf_symbol = symbol + ".NS"
    try:
        # Download 3 years of daily data
        data = yf.download(yf_symbol, period="3y", interval="1d", progress=False)
        if data.empty or 'Close' not in data:
            logger.warning(f"No data for {symbol}")
            continue
        last_close = data['Close'].iloc[-1]
        stock_info = {
            'Symbol': symbol,
            'Last Close': last_close
        }
        for label, days in periods.items():
            if len(data) > days:
                past_close = data['Close'].iloc[-days-1]
                pct_change = ((last_close / past_close) - 1) * 100
                stock_info[label] = pct_change
            else:
                stock_info[label] = None
        results.append(stock_info)
        logger.info(f"{symbol}: {stock_info}")
    except Exception as e:
        logger.warning(f"{symbol}: Error fetching or processing data: {e}")

try:
    os.makedirs("files", exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    logger.info(f"Saved {len(results)} Nifty 200 stocks with change stats to {output_path}")
except Exception as e:
    logger.error(f"Failed to save JSON file: {e}")
    raise
