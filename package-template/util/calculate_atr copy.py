import json
import os
import pandas as pd
import numpy as np

# --- Configuration ---
ATR_PERIOD = 14                  # Number of days to calculate ATR
ATR_MULTIPLIER = 2.5             # Multiplier for trailing stop loss

# Adjust paths: holdings.json and atr.json are now in the "files" folder.
HOLDINGS_FILE = os.path.join(os.path.dirname(__file__), "..", "files", "holding.json")
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "..", "files", "atr.json")

def calculate_atr(high_prices, low_prices, close_prices, period):
    """
    Calculate the Average True Range (ATR) using a simple rolling mean.
    """
    df = pd.DataFrame({
        'high': high_prices,
        'low': low_prices,
        'close': close_prices
    })
    
    # Calculate True Range (TR)
    df['tr1'] = df['high'] - df['low']
    df['tr2'] = (df['high'] - df['close'].shift(1)).abs()
    df['tr3'] = (df['low'] - df['close'].shift(1)).abs()
    df['true_range'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
    
    # Calculate ATR using a simple rolling mean
    atr_values = df['true_range'].rolling(window=period).mean()
    return atr_values.iloc[-1] if not atr_values.empty else 0

def process_holdings():
    # Load existing holdings from holdings.json
    if not os.path.exists(HOLDINGS_FILE):
        print(f"Holdings file not found: {HOLDINGS_FILE}")
        return

    with open(HOLDINGS_FILE, 'r', encoding='utf-8') as f:
        holdings_data = json.load(f)

    # Supports both structures: holdings may be a list directly or under a "holdings" key.
    holdings = holdings_data.get("holdings", holdings_data)
    
    for holding in holdings:
        # Ensure required fields exist: purchase_price, highest_price_reached, last_14_days_data
        if ("purchase_price" not in holding or 
            "highest_price_reached" not in holding or 
            "last_14_days_data" not in holding):
            continue  # Skip entries with missing required data
        
        # Convert last_14_days_data to a DataFrame
        df = pd.DataFrame(holding["last_14_days_data"])
        # Ensure numeric types for calculations
        for col in ['high', 'low', 'close']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        if df.empty or df['high'].isnull().all() or df['low'].isnull().all() or df['close'].isnull().all():
            atr_value = 0
        else:
            atr_value = calculate_atr(df['high'], df['low'], df['close'], ATR_PERIOD)
        
        holding["atr_value"] = atr_value
        
        # Calculate trailing stop loss:
        # trailing_stop_loss = highest_price_reached - (atr_value * ATR_MULTIPLIER)
        trailing_sl = holding["highest_price_reached"] - (atr_value * ATR_MULTIPLIER)
        # Ensure the trailing stop loss does not fall below purchase price.
        trailing_sl = max(holding["purchase_price"], trailing_sl)
        holding["trailing_stop_loss"] = trailing_sl
        
        # For simulation, use the latest close value from historical data as the current price.
        current_price = df['close'].iloc[-1] if not df.empty and 'close' in df.columns else holding["purchase_price"]
        
        # Mark the action: SELL if current price <= trailing stop loss, else HOLD.
        holding["action"] = "SELL" if current_price <= trailing_sl else "HOLD"
    
    # Save the updated holdings with ATR calculations to atr.json
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f_out:
        json.dump(holdings, f_out, indent=4)
    
    print(f"ATR calculation and sell/hold marking completed. Results saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    process_holdings()