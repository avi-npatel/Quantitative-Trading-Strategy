import yfinance as yf
import pandas as pd
import numpy as np

def calculate_dynamic_levels(ticker_symbol, atr_period=14, sl_multiplier=2.0, tp_multiplier=3.0):
    """
    Fetches historical data and calculates a volatility-based Trailing Stop Loss 
    and Take Profit.
    
    Parameters:
    ticker_symbol (str): The stock ticker (e.g., 'AAPL', 'TSLA').
    atr_period (int): Lookback period for ATR (14 is standard).
    sl_multiplier (float): Multiplier for the trailing stop loss distance.
    tp_multiplier (float): Multiplier for the take profit distance.
    """
    print(f"Fetching maximum historical data for {ticker_symbol}...")
    
    # Fetch Data
    stock = yf.Ticker(ticker_symbol)
    df = stock.history(period="max")
    
    if df.empty:
        return "No data found. Please check the ticker symbol."

    # Calculate True Range (TR)
    df['High-Low'] = df['High'] - df['Low']
    df['High-PrevClose'] = abs(df['High'] - df['Close'].shift(1))
    df['Low-PrevClose'] = abs(df['Low'] - df['Close'].shift(1))
    
    df['TR'] = df[['High-Low', 'High-PrevClose', 'Low-PrevClose']].max(axis=1)
    
    # Calculate Average True Range (ATR)
    df['ATR'] = df['TR'].rolling(window=atr_period).mean()
    
    # Extract Latest Data to determine current optimal levels
    latest_price = df['Close'].iloc[-1]
    latest_atr = df['ATR'].iloc[-1]
    latest_date = df.index[-1].strftime('%Y-%m-%d')
    

    # Trailing Stop: Price - (ATR * Multiplier)
    trailing_stop_price = latest_price - (latest_atr * sl_multiplier)
    
    # Take Profit: Price + (ATR * Multiplier)
    take_profit_price = latest_price + (latest_atr * tp_multiplier)
    
    # Rresults
    results = {
        "Ticker": ticker_symbol.upper(),
        "Date of Analysis": latest_date,
        "Latest Close Price": round(latest_price, 2),
        "Current ATR (14-day)": round(latest_atr, 2),
        "Suggested Trailing Stop Loss": round(trailing_stop_price, 2),
        "Suggested Take Profit": round(take_profit_price, 2),
        "Risk/Reward Ratio": f"1 : {tp_multiplier / sl_multiplier}"
    }
    
    return results


# Ticker Symbol
TARGET_STOCK = "NVDA" 

optimal_levels = calculate_dynamic_levels(TARGET_STOCK)

print("\n--- Results ---")
for key, value in optimal_levels.items():
    print(f"{key}: {value}")