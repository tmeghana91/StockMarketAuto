import yfinance as yf
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def download_data(ticker="RELIANCE.NS", period="1y"):
    logger.info(f"Downloading data for {ticker} for period {period}")
    try:
        data = yf.download(ticker, period=period)
        if data.empty:
            logger.error("No data downloaded. The ticker may be delisted or invalid.")
            return None
        return data
    except Exception as e:
        logger.error(f"Error downloading data for {ticker}: {e}")
        return None

if __name__ == "__main__":
    ticker = "RELIANCE.NS"
    data = download_data(ticker)
    if data is not None:
        # Display the first few rows of the downloaded data
        print("Downloaded data for", ticker)
        print(data.head())
    else:
        print("Failed to download data.")