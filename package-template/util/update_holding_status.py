import json
import os

base_dir = os.path.dirname(__file__)
holding_path = os.path.join(base_dir, '../files/holding.json')
fundamental_path = os.path.join(base_dir, '../files/fundamental_holdings.json')

# Load holdings
with open(holding_path, 'r', encoding='utf-8') as f:
    holdings_data = json.load(f)

holdings = holdings_data['result']

# Load fundamentals
with open(fundamental_path, 'r', encoding='utf-8') as f:
    fundamentals = json.load(f)

def is_strong(fund):
    try:
        pe = float(fund.get('peRatio', 'nan'))
        roe = float(fund.get('roe', 'nan'))
        de = float(fund.get('debtToEquity', 'nan'))
        return (pe < 25) and (roe > 0.15) and (de < 1.5)
    except Exception:
        return False

for h in holdings:
    symbol = h.get('nseTradingSymbol', '').replace('-EQ', '') + '.NS'
    fund = fundamentals.get(symbol)
    if not fund and h.get('bseTradingSymbol'):
        symbol = h['bseTradingSymbol'] + '.BO'
        fund = fundamentals.get(symbol)
    if fund and is_strong(fund):
        h['status'] = 'Strong'
    else:
        h['status'] = 'Weak'

# Save the updated holdings back to holding.json
with open(holding_path, 'w', encoding='utf-8') as f:
    json.dump(holdings_data, f, indent=2)

print("Updated holding.json with status for each record.")