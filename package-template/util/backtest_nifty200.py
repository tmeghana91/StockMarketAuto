import json
import yfinance as yf
import pandas as pd
import os
import logging

# Setup logging to D:\Py_code\Stock_Trading_Auto\log
log_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..', 'log')
os.makedirs(log_dir, exist_ok=True)
log_path = os.path.join(log_dir, 'nifty200_backtest.log')
logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Parameters
ENTRY_DATE = "2023-01-02"  # Set your intended buy date (from 2023)
TRAILING_STOP_PCT = 0.15   # 15% trailing stop
ATR_MULTIPLIER = 2         # ATR-based stop-loss multiplier
MAX_HOLDING = 120          # 120 trading days
MOVING_AVG_WINDOW = 200    # 200-day moving average for trend filter

# Load buy list
buy_list_path = os.path.join("recommendations", "nifty200_buy.json")
with open(buy_list_path, "r") as f:
    buy_list = json.load(f)

results = []

for stock_info in buy_list:
    symbol = stock_info["Symbol"]
    yf_symbol = symbol + ".NS"
    try:
        data = yf.download(yf_symbol, start="2022-01-01", end="2024-01-01", progress=False)
        data = data.reset_index()
        # Calculate 200-day moving average for trend filter
        data['MA200'] = data['Close'].rolling(window=MOVING_AVG_WINDOW).mean()
        # Calculate ATR for ATR-based stop-loss
        data['H-L'] = data['High'] - data['Low']
        data['H-PC'] = abs(data['High'] - data['Close'].shift(1))
        data['L-PC'] = abs(data['Low'] - data['Close'].shift(1))
        data['TR'] = data[['H-L', 'H-PC', 'L-PC']].max(axis=1)
        data['ATR'] = data['TR'].rolling(window=14).mean()
        entry_row = data[data['Date'] == pd.to_datetime(ENTRY_DATE)]
        if entry_row.empty:
            logger.info(f"{symbol}: Buy date {ENTRY_DATE} not found in data.")
            continue
        entry_idx_list = entry_row.index.tolist()
        if not entry_idx_list:
            logger.info(f"{symbol}: Buy date {ENTRY_DATE} not found in data.")
            continue
        entry_idx = entry_idx_list[0]
        entry_price = float(entry_row.loc[entry_idx, 'Close'])
        # Trend filter: only buy if above 200-day MA
        ma200 = float(entry_row.loc[entry_idx, 'MA200'])
        if entry_price < ma200 or pd.isna(ma200):
            logger.info(f"{symbol}: Skipped, not above 200-day MA on entry date.")
            continue
        highest_close = entry_price
        exit_price = entry_price
        exit_date = ENTRY_DATE
        exit_reason = "Max holding period"
        atr_on_entry = float(entry_row.loc[entry_idx, 'ATR'])
        for i in range(entry_idx + 1, min(entry_idx + 1 + MAX_HOLDING, len(data))):
            close = float(data.loc[i, 'Close'])
            date = data.loc[i, 'Date']
            if close > highest_close:
                highest_close = close
            # Both stops: trailing and ATR-based
            stop_trailing = highest_close * (1 - TRAILING_STOP_PCT)
            stop_atr = highest_close - ATR_MULTIPLIER * atr_on_entry
            stop = max(stop_trailing, stop_atr)  # Use the tighter stop
            if close < stop:
                exit_price = close
                exit_date = date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date)
                if close < stop_trailing and close < stop_atr:
                    exit_reason = f"Trailing & ATR stop hit"
                elif close < stop_trailing:
                    exit_reason = "Trailing stop hit"
                else:
                    exit_reason = "ATR stop hit"
                break
        else:
            # If not stopped out, sell at the end of holding period
            idx = min(entry_idx + MAX_HOLDING, len(data)-1)
            exit_price = float(data.loc[idx, 'Close'])
            exit_date = data.loc[idx, 'Date'].strftime('%Y-%m-%d') if hasattr(data.loc[idx, 'Date'], 'strftime') else str(data.loc[idx, 'Date'])
        ret = (exit_price / entry_price - 1) * 100
        results.append({
            "Symbol": symbol,
            "Entry Date": ENTRY_DATE,
            "Entry Price": entry_price,
            "Exit Date": exit_date,
            "Exit Price": exit_price,
            "Exit Reason": exit_reason,
            "Return %": ret
        })
        logger.info(f"{symbol}: Entry {ENTRY_DATE} at {entry_price:.2f}, Exit {exit_date} at {exit_price:.2f} ({exit_reason}), Return {ret:.2f}%")
    except Exception as e:
        logger.warning(f"{symbol}: Error in backtest: {e}")

# Save results
os.makedirs("files", exist_ok=True)
backtest_output_path = os.path.join("files", "nifty200_backtest.json")
with open(backtest_output_path, "w") as f:
    json.dump(results, f, indent=2)
logger.info(f"Backtest complete. Results saved to {backtest_output_path}")