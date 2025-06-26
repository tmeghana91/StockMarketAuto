import json
import yfinance as yf
import os

base_dir = os.path.dirname(__file__)
holding_path = os.path.join(base_dir, '../files/holding.json')

# Load your holdings
with open(holding_path, "r", encoding="utf-8") as f:
    holdings = json.load(f)["result"]

# Prepare a list of NSE symbols (add .NS for yfinance)
symbols = []
symbol_map = {}
for h in holdings:
    symbol = h.get("nseTradingSymbol", "")
    if symbol:
        yf_symbol = symbol.replace("-EQ", "") + ".NS"
        symbols.append(yf_symbol)
        symbol_map[yf_symbol] = h

# Fetch data from yfinance
fundamentals = {}
for sym in symbols:
    try:
        t = yf.Ticker(sym)
        info = t.info
        fundamentals[sym] = {
            "symbol": symbol_map[sym].get("nseTradingSymbol", ""),
            "name": info.get("shortName", ""),
            "currentPrice": info.get("currentPrice", ""),
            "peRatio": info.get("trailingPE", ""),
            "marketCap": info.get("marketCap", ""),
            "dividendYield": info.get("dividendYield", ""),
            "netProfit": info.get("netIncomeToCommon", ""),
            "roe": info.get("returnOnEquity", ""),
            "debtToEquity": info.get("debtToEquity", ""),
            "pbRatio": info.get("priceToBook", ""),
            "eps": info.get("trailingEps", ""),
            "industry": info.get("industry", ""),
            "sector": info.get("sector", ""),
            "promoterHolding": "",  # Not available in yfinance
        }
    except Exception as e:
        fundamentals[sym] = {"symbol": sym, "error": str(e)}

# Save as JSON
output_path = os.path.join(os.path.dirname(__file__), "../files/fundamental_holdings.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(fundamentals, f, indent=2)

print(f"Fundamental data saved to {output_path}")