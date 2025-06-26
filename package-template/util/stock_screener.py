import yfinance as yf
import pandas as pd
import logging
import os

# Setup logging to D:\Py_code\Stock_Trading_Auto\log
log_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..', 'log')
os.makedirs(log_dir, exist_ok=True)
log_path = os.path.join(log_dir, 'stock_screener.log')
logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# List of NSE symbols to screen (add more as needed)
symbols = [
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
    "SBIN.NS", "LT.NS", "HINDUNILVR.NS", "KOTAKBANK.NS", "BAJFINANCE.NS"
]

# Loosened screening thresholds
MIN_EPS_GROWTH = 0.10
MIN_SALES_GROWTH = 0.07
MIN_ROE = 0.12
MAX_DEBT_TO_EQUITY = 0.7
MIN_PRICE_ABOVE_50DMA = False  # Only require above 200DMA
MIN_PRICE_ABOVE_200DMA = True

results = []

for symbol in symbols:
    try:
        stock = yf.Ticker(symbol)
        info = stock.info

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
        hist = stock.history(period='6mo')
        if len(hist) < 200:
            logger.info(f"{symbol} failed: Not enough data for 200DMA")
            continue  # Not enough data for 200DMA

        close = hist['Close']
        dma_50 = close.rolling(50).mean()
        dma_200 = close.rolling(200).mean()
        last_close = close.iloc[-1]

        if MIN_PRICE_ABOVE_50DMA and last_close < dma_50.iloc[-1]:
            logger.info(f"{symbol} failed 50DMA: Last close {last_close} < 50DMA {dma_50.iloc[-1]}")
            continue
        if MIN_PRICE_ABOVE_200DMA and last_close < dma_200.iloc[-1]:
            logger.info(f"{symbol} failed 200DMA: Last close {last_close} < 200DMA {dma_200.iloc[-1]}")
            continue

        results.append({
            "Symbol": symbol,
            "EPS Growth": eps_growth,
            "Sales Growth": sales_growth,
            "ROE": roe,
            "Debt/Equity": debt_to_equity,
            "Last Close": last_close,
            "50DMA": dma_50.iloc[-1],
            "200DMA": dma_200.iloc[-1]
        })
    except Exception as e:
        logger.warning(f"Error processing {symbol}: {e}")

# Display results
if results:
    df = pd.DataFrame(results)
    logger.info("=== Growing Stocks Matching Criteria ===\n" + df.to_string(index=False))
else:
    logger.info("No stocks matched the criteria.")
