import json
import logging
import os

# Setup logging to D:\Py_code\Stock_Trading_Auto\log
log_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..', 'log')
os.makedirs(log_dir, exist_ok=True)
log_path = os.path.join(log_dir, 'portfolio_allocation.log')
logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# CONFIGURABLE THRESHOLDS
MAX_STOCK_WEIGHT = 0.10   # 10% max per stock
MAX_SECTOR_WEIGHT = 0.25  # 25% max per sector

# Load holdings (from atr.json or holding.json)
with open("files/atr.json", "r") as f:
    holdings = json.load(f)

# Calculate position values and total portfolio value
for h in holdings:
    h["position_value"] = h["totalQuantity"] * h["previousDayClose"]
total_value = sum(h["position_value"] for h in holdings)

# Calculate weights
for h in holdings:
    h["weight"] = h["position_value"] / total_value if total_value else 0

# Flag overexposed stocks
logger.info("=== Overexposed Stocks (>{:.0f}% of portfolio) ===".format(MAX_STOCK_WEIGHT*100))
for h in holdings:
    if h["weight"] > MAX_STOCK_WEIGHT:
        logger.info(f"{h['bseTradingSymbol']}: {h['weight']*100:.2f}%")

# Aggregate by sector (if available)
sector_map = {}
for h in holdings:
    sector = h.get("sector", "Unknown")
    sector_map.setdefault(sector, 0)
    sector_map[sector] += h["position_value"]

logger.info("\n=== Overexposed Sectors (>{:.0f}% of portfolio) ===".format(MAX_SECTOR_WEIGHT*100))
for sector, value in sector_map.items():
    weight = value / total_value if total_value else 0
    if weight > MAX_SECTOR_WEIGHT:
        logger.info(f"{sector}: {weight*100:.2f}%")

# Print full allocation for review
logger.info("\n=== Full Portfolio Allocation ===")
for h in holdings:
    logger.info(f"{h['bseTradingSymbol']}: {h['weight']*100:.2f}% (Value: {h['position_value']:.2f})")
