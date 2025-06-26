import pandas as pd
import json
import os
import logging

# Setup logging to D:\Py_code\Stock_Trading_Auto\log
log_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..', 'log')
os.makedirs(log_dir, exist_ok=True)
log_path = os.path.join(log_dir, 'csv_to_json.log')
logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

csv_path = "files/ind_nifty200list.csv"
output_path = os.path.join("files", "nifty200.json")

try:
    logger.info(f"Reading CSV file: {csv_path}")
    df = pd.read_csv(csv_path)
    logger.info(f"CSV columns: {list(df.columns)}")
    symbols = df['Symbol'].tolist()
    logger.info(f"Extracted {len(symbols)} symbols.")
except Exception as e:
    logger.error(f"Error reading or parsing CSV: {e}")
    raise

try:
    os.makedirs("files", exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(symbols, f, indent=2)
    logger.info(f"Saved {len(symbols)} symbols to {output_path}")
except Exception as e:
    logger.error(f"Error saving JSON file: {e}")
    raise