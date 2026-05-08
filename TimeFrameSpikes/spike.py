import asyncio
from alpaca.data.live import StockDataStream
from datetime import datetime
import pandas as pd

# Initialize Alpaca Stream (Replace with Paper Trading keys)
API_KEY = 'PKPWEEHLY7PXLM2LMCI6WOF43A'
SECRET_KEY = 'D5ZEcn71xiMJyhTiWkruhuJBo5bSvcveYc2mgVmYV2L8'
stream = StockDataStream(API_KEY, SECRET_KEY)

# Dictionary to hold rolling minute data for each ticker
# Format: {'AAPL': {'close': [150.1, 150.5...], 'volume': [1000, 1500...]}}
market_data = {}

# Constants for our strategy
MAX_PRICE = 40.00 # Keeping it under $40 to maximize leverage of a smaller account balance
MIN_PRICE = 1.00

def check_930_momentum(symbol, df):
    """Looks for 3 consecutive minutes of climbing price and volume at 9:30 AM"""
    if len(df) < 3: return
    
    # Check if the last 3 closes are progressively higher (Sharp Increase)
    climbing = df['close'].iloc[-1] > df['close'].iloc[-2] > df['close'].iloc[-3]
    
    # Check if the last 3 closes are progressively lower (Sharp Decrease)
    dropping = df['close'].iloc[-1] < df['close'].iloc[-2] < df['close'].iloc[-3]
    
    if climbing:
        print_alert("9:30 AM BULLISH CLIMB", symbol, df['close'].iloc[-1])
    elif dropping:
        print_alert("9:30 AM BEARISH DROP", symbol, df['close'].iloc[-1])

def check_1030_velocity(symbol, df):
    """Looks for a sudden violent spike in price and volume at exactly 10:30 AM"""
    if len(df) < 10: return # Need history for average volume
    
    current_close = df['close'].iloc[-1]
    previous_close = df['close'].iloc[-2]
    current_vol = df['volume'].iloc[-1]
    
    # Calculate average volume of the last 10 minutes (excluding current)
    avg_vol_10m = df['volume'].iloc[-11:-1].mean()
    
    # Calculate % change of this specific minute
    pct_change = ((current_close - previous_close) / previous_close) * 100
    
    # Trigger: 1.5% move in one minute AND Volume is 3x the recent average
    if pct_change >= 1.5 and current_vol > (avg_vol_10m * 3):
        print_alert("10:30 AM UPSIDE VELOCITY SPIKE", symbol, current_close)
        
    elif pct_change <= -1.5 and current_vol > (avg_vol_10m * 3):
        print_alert("10:30 AM DOWNSIDE VELOCITY SPIKE", symbol, current_close)

def print_alert(alert_type, symbol, price):
    """Formats the output and generates a clickable TradingView link"""
    tv_link = f"https://www.tradingview.com/chart/?symbol={symbol}"
    print(f"\n[ALERT] {alert_type} | Ticker: {symbol} | Price: ${price:.2f}")
    print(f"Chart: {tv_link}\n" + "-"*50)

async def handle_bar(bar):
    """This function is triggered automatically every time a 1-minute candle closes"""
    symbol = bar.symbol
    close_price = bar.close
    volume = bar.volume
    timestamp = bar.timestamp # UTC time
    
    # Filter out expensive stocks 
    if not (MIN_PRICE <= close_price <= MAX_PRICE):
        return

    # Initialize ticker in our dictionary if it's new
    if symbol not in market_data:
        market_data[symbol] = {'close': [], 'volume': []}
        
    # Append new data and keep only the last 15 minutes to save memory
    market_data[symbol]['close'].append(close_price)
    market_data[symbol]['volume'].append(volume)
    market_data[symbol]['close'] = market_data[symbol]['close'][-15:]
    market_data[symbol]['volume'] = market_data[symbol]['volume'][-15:]

    # Convert dictionary to a quick Pandas DataFrame for easy math
    df = pd.DataFrame(market_data[symbol])

    # Time-based triggers
    current_time = datetime.now()
    
    # 1. Run the 9:30 AM momentum logic between 9:30 and 9:35
    if current_time.hour == 9 and 30 <= current_time.minute <= 35:
        check_930_momentum(symbol, df)
        
    # 2. Run the velocity spike logic continuously from 10:30 AM until the program is stopped
    elif (current_time.hour == 10 and current_time.minute >= 30) or current_time.hour > 10:
        check_1030_velocity(symbol, df)
    
    # --- HEARTBEAT ---
    # Print a ping using a stock under $40 so we know data is flowing
    if symbol == 'SOFI': 
        print(f"[{current_time.strftime('%H:%M:%S')}] Stream active... SOFI currently at ${close_price:.2f}")

# Subscribe to all minute bars ('*')
stream.subscribe_bars(handle_bar, '*')

# Start the live connection
print("Initializing Pulse-Seeker... Waiting for market data.")
stream.run()