import json
import yfinance as yf
import os

# Load your holdings
with open("../files/holding.json", "r") as f:
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
            "promoterHolding": "",  # Not available in yfinance
        }
    except Exception as e:
        fundamentals[sym] = {"name": sym, "error": str(e)}

# Generate HTML
html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Fundamental Analysis</title>
    <style>
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ccc; padding: 8px; }
        th { background: #0074d9; color: #fff; }
        tr:nth-child(even) { background: #f2f7fb; }
        tr:nth-child(odd) { background: #fff; }
    </style>
</head>
<body>
<h2>Fundamental Analysis of Holdings</h2>
<table>
<thead>
<tr>
    <th>Symbol</th>
    <th>Name</th>
    <th>CMP</th>
    <th>P/E</th>
    <th>Market Cap</th>
    <th>Div Yld</th>
    <th>Net Profit</th>
    <th>ROE</th>
    <th>Debt/Eq</th>
    <th>P/B</th>
    <th>EPS</th>
</tr>
</thead>
<tbody>
"""

for sym in symbols:
    f = fundamentals.get(sym, {})
    h = symbol_map[sym]
    html += "<tr>"
    html += f"<td>{h.get('nseTradingSymbol','')}</td>"
    html += f"<td>{f.get('name','')}</td>"
    html += f"<td>{f.get('currentPrice','')}</td>"
    html += f"<td>{f.get('peRatio','')}</td>"
    html += f"<td>{f.get('marketCap','')}</td>"
    html += f"<td>{f.get('dividendYield','')}</td>"
    html += f"<td>{f.get('netProfit','')}</td>"
    html += f"<td>{f.get('roe','')}</td>"
    html += f"<td>{f.get('debtToEquity','')}</td>"
    html += f"<td>{f.get('pbRatio','')}</td>"
    html += f"<td>{f.get('eps','')}</td>"
    html += "</tr>"

html += """
</tbody>
</table>
</body>
</html>
"""

# Save HTML
output_path = os.path.join(os.path.dirname(__file__), "../files/fundamental_holdings.html")
with open(output_path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"Fundamental analysis HTML generated at {output_path}")