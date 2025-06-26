import json
import yfinance as yf
import pandas as pd
import os
import logging
import requests

# Setup logging to D:\Py_code\Stock_Trading_Auto\log
log_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..', 'log')
os.makedirs(log_dir, exist_ok=True)
log_path = os.path.join(log_dir, 'nifty200_buy.log')
# Set up logging to both file and console with DEBUG level
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# File handler
file_handler = logging.FileHandler(log_path)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Remove default handlers if present
if logger.hasHandlers():
    logger.handlers = [file_handler, console_handler]

# Ensure NSEEQ.json exists, else download
nseeq_json_path = os.path.join("static", "NSEEQ.json") # Updated path to static
if not os.path.exists(nseeq_json_path):
    url = "https://api.iiflcapital.com/v1/contractfiles/NSEEQ.json"
    try:
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        with open(nseeq_json_path, "wb") as f:
            f.write(resp.content)
        logger.info(f"Downloaded NSEEQ.json to {nseeq_json_path}")
    except Exception as e:
        logger.error(f"Failed to download NSEEQ.json: {e}")
        raise SystemExit(1)

# Load Nifty 200 symbols
with open("files/nifty200.json", "r") as f:
    symbols = json.load(f)

NEAR_HIGH_THRESHOLD = 0.10  # 10% within 52-week high
MIN_EPS_GROWTH = 0.05
MIN_SALES_GROWTH = 0.05
MIN_ROE = 0.10
MAX_DEBT_TO_EQUITY = 1.0
MAX_PER_SECTOR = 15  # Max stocks per sector

# News sentiment analysis
POSITIVE_WORDS = ["growth", "profit", "record", "expansion", "approval", "acquisition", "strong", "beats", "upgrade"]
NEGATIVE_WORDS = ["loss", "decline", "drop", "fraud", "investigation", "lawsuit", "weak", "misses", "downgrade"]

def get_news_sentiment(headlines):
    score = 0
    for headline in headlines:
        h = headline.lower()
        if any(word in h for word in POSITIVE_WORDS):
            score += 1
        if any(word in h for word in NEGATIVE_WORDS):
            score -= 1
    if score > 0:
        return "Positive"
    elif score < 0:
        return "Negative"
    else:
        return "Neutral"

buy_list = []
sector_counts = {}

for symbol in symbols:
    try:
        yf_symbol = symbol + ".NS"
        stock = yf.Ticker(yf_symbol)
        info = stock.info
        sector = info.get('sector', 'Unknown')
        sector_counts.setdefault(sector, 0)
        if sector_counts[sector] >= MAX_PER_SECTOR:
            logger.info(f"{symbol} skipped: sector cap reached for {sector}")
            continue

        # Fundamental checks
        eps_growth = info.get('earningsQuarterlyGrowth', 0)
        sales_growth = info.get('revenueGrowth', 0)
        roe = info.get('returnOnEquity', 0)
        debt_to_equity = info.get('debtToEquity', 1)

        if eps_growth < MIN_EPS_GROWTH:
            logger.info(f"{symbol} failed EPS growth: {eps_growth}")
            continue
        if sales_growth < MIN_SALES_GROWTH:
            logger.info(f"{symbol} failed Sales growth: {sales_growth}")
            continue
        if roe < MIN_ROE:
            logger.info(f"{symbol} failed ROE: {roe}")
            continue
        if debt_to_equity > MAX_DEBT_TO_EQUITY:
            logger.info(f"{symbol} failed Debt/Equity: {debt_to_equity}")
            continue

        # Technical checks
        hist = stock.history(period='1y')
        if len(hist) < 200:
            logger.info(f"{symbol} failed: Not enough data for 200DMA/52W high")
            continue

        close = hist['Close']
        dma_200 = close.rolling(200).mean()
        last_close = close.iloc[-1]
        high_52w = close.max()

        if last_close < dma_200.iloc[-1]:
            logger.info(f"{symbol} failed 200DMA: Last close {last_close} < 200DMA {dma_200.iloc[-1]}")
            continue
        if last_close < (1 - NEAR_HIGH_THRESHOLD) * high_52w:
            logger.info(f"{symbol} not near 52W high: Last close {last_close}, 52W high {high_52w}")
            continue

        # News filter
        try:
            news_items = stock.news
            headlines = [item['title'] for item in news_items if 'title' in item][:5]
            sentiment = get_news_sentiment(headlines)
            logger.info(f"{symbol} news sentiment: {sentiment}")
            if sentiment == "Negative":
                logger.info(f"{symbol} skipped due to negative news sentiment.")
                continue
        except Exception as e:
            logger.warning(f"{symbol} news fetch failed: {e}")
            sentiment = "Unknown"

        # Calculate multi-timeframe percentage changes using candle data file if available
        periods = {
            "1w": 5,
            "14d": 14,
            "1m": 21,
            "3m": 63,
            "6m": 126,
            "1y": 252,
            "2y": 504,
            "3y": 756
        }
        pct_changes = {}
        candle_file = os.path.join("files", f"{symbol}-EQ_candles.json")
        close_series = None
        # If candle file does not exist, fetch from IIFL API
        if not os.path.exists(candle_file):
            # Parse NSEEQ.json to get instrumentId
            instrument_id = None
            logger.debug(f"Looking up instrumentId for symbol: {symbol}")
            try:
                with open(nseeq_json_path, "r", encoding="utf-8") as jf:
                    contracts = json.load(jf)
                    for row in contracts:
                        trading_symbol = f"{symbol}-EQ"
                        if row.get('tradingSymbol') == trading_symbol and row.get('exchange') == 'NSEEQ':
                            instrument_id = row.get('instrumentId')
                            logger.debug(f"Found instrumentId {instrument_id} for tradingSymbol {trading_symbol}")
                            break
            except Exception as e:
                logger.warning(f"Error reading NSEEQ.json: {e}")
            if not instrument_id:
                logger.warning(f"InstrumentId not found for symbol: {symbol}")
            if instrument_id:
                # Read auth token
                auth_token_path = os.path.join("files", "auth_token.txt")
                try:
                    with open(auth_token_path, "r", encoding="utf-8") as f:
                        raw_token = f.read().strip()
                        if not raw_token.lower().startswith("bearer "):
                            AUTH_TOKEN = f"Bearer {raw_token}"
                        else:
                            AUTH_TOKEN = raw_token
                    logger.debug(f"Read auth token for IIFL API")
                except Exception as e:
                    logger.error(f"Could not read auth token: {e}")
                    AUTH_TOKEN = None
                if AUTH_TOKEN:
                    from datetime import datetime, timedelta
                    URL = "https://api.iiflcapital.com/v1/marketdata/historicaldata"
                    HEADERS = {
                        "Content-Type": "application/json",
                        "Authorization": AUTH_TOKEN
                    }
                    to_date = datetime.now()
                    from_date = to_date - timedelta(days=3*365)
                    to_date_str = to_date.strftime("%d-%b-%Y").lower()
                    from_date_str = from_date.strftime("%d-%b-%Y").lower()
                    payload = {
                        "exchange": "NSEEQ",
                        "instrumentId": str(instrument_id),
                        "interval": "1 day",
                        "fromDate": from_date_str,
                        "toDate": to_date_str
                    }
                    logger.debug(f"Requesting candle data for {symbol} (instrumentId={instrument_id}) from {from_date_str} to {to_date_str}")
                    logger.info(f"IIFL API Request: URL={URL}, HEADERS={HEADERS}, PAYLOAD={payload}")
                    print(f"IIFL API Request: URL={URL}, HEADERS={HEADERS}, PAYLOAD={payload}")
                    try:
                        resp = requests.post(URL, headers=HEADERS, json=payload, timeout=60)
                        logger.info(f"IIFL API Response: status_code={resp.status_code}, body={resp.text}")
                        print(f"IIFL API Response: status_code={resp.status_code}, body={resp.text}")
                        resp.raise_for_status()
                        data = resp.json()
                        with open(candle_file, "w", encoding="utf-8") as outf:
                            json.dump(data, outf, indent=2)
                        logger.info(f"Fetched and saved candle data for {symbol} to {candle_file}")
                    except Exception as e:
                        logger.error(f"Failed to fetch candle data for {symbol}: {e}")
                else:
                    logger.warning(f"No valid auth token for IIFL API, skipping candle fetch for {symbol}")
            else:
                logger.warning(f"Skipping candle fetch for {symbol} due to missing instrumentId")
        try:
            if os.path.exists(candle_file):
                logger.debug(f"Reading candle data from {candle_file}")
                with open(candle_file, "r", encoding="utf-8") as cf:
                    candle_data = json.load(cf)
                    candles = candle_data["result"][0]["candles"]
                    close_series = [c[4] for c in candles]
            else:
                logger.debug(f"Candle file not found for {symbol}, falling back to yfinance data")
                close_series = close.reset_index(drop=True).tolist()
        except Exception as e:
            logger.warning(f"{symbol} candle file read failed: {e}")
            close_series = close.reset_index(drop=True).tolist()
        for label, days in periods.items():
            if close_series and len(close_series) > days:
                past_close = close_series[-days-1]
                pct_change = ((last_close - past_close) / past_close) * 100
                pct_changes[f"Change_{label}"] = pct_change
            else:
                pct_changes[f"Change_{label}"] = None

        buy_entry = {
            "Symbol": symbol,
            "Sector": sector,
            "Last Close": last_close,
            "52W High": high_52w,
            "Pct from High": (last_close / high_52w - 1) * 100,
            "News Sentiment": sentiment,
            "BUY": True
        }
        buy_entry.update(pct_changes)
        buy_list.append(buy_entry)
        sector_counts[sector] += 1
        logger.info(f"{symbol} marked as BUY")
    except Exception as e:
        logger.warning(f"Error processing {symbol}: {e}")

# Save buy list
os.makedirs("recommendations", exist_ok=True)
with open("recommendations/nifty200_buy.json", "w") as f:
    json.dump(buy_list, f, indent=2)
logger.info(f"Saved {len(buy_list)} stocks marked as BUY to recommendations/nifty200_buy.json")
