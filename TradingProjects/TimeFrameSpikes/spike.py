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
    """Optimized 9:30 AM logic: 3-min climb, surging volume, and anti-wick trap filter"""
    if len(df) < 3: return
    
    # Price Step-Ladder
    climbing = df['close'].iloc[-1] > df['close'].iloc[-2] > df['close'].iloc[-3]
    dropping = df['close'].iloc[-1] < df['close'].iloc[-2] < df['close'].iloc[-3]
    
    # Volume Conviction
    current_vol = df['volume'].iloc[-1]
    minute_1_vol = df['volume'].iloc[-3]
    min_volume = 50000 
    surge_factor = 1.5 
    
    volume_is_strong = (current_vol >= min_volume) and (current_vol > minute_1_vol * surge_factor)
    
    # The Wick Filter (Trap Detector)
    open_price = df['open'].iloc[-1]
    close_price = df['close'].iloc[-1]
    high_price = df['high'].iloc[-1]
    low_price = df['low'].iloc[-1]
    
    total_range = high_price - low_price
    if total_range == 0: return # Prevent divide-by-zero errors on flat candles
    
    # Calculate where the close sits as a percentage (0.0 is the very bottom, 1.0 is the absolute peak)
    close_percentile = (close_price - low_price) / total_range
    
    # For a bullish climb, the close MUST be in the top 30% (percentile >= 0.70)
    bullish_no_trap = close_percentile >= 0.70
    
    # For a bearish drop, the close MUST be in the bottom 30% (percentile <= 0.30)
    bearish_no_trap = close_percentile <= 0.30
    
    # 4. The Ultimate Trigger
    if climbing and volume_is_strong and bullish_no_trap:
        print_alert("9:30 AM BULL BREAKOUT (STRONG CLOSE)", symbol, close_price)
        
    elif dropping and volume_is_strong and bearish_no_trap:
        print_alert("9:30 AM BEAR DROPDOWN (STRONG CLOSE)", symbol, close_price)


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

def check_downtime_anomaly(symbol, df):
    """Catches sudden, abnormally large green candles during the mid-morning lull"""
    # We need at least 10 minutes of history to know what "normal" looks like
    if len(df) < 11: return 

    # Is it a green candle?
    current_open = df['open'].iloc[-1]
    current_close = df['close'].iloc[-1]
    
    if current_close <= current_open: return # It's red or flat, ignore it

    current_body_size = current_close - current_open

    # Calculate "Normal" (Average body size of the last 10 candles)
    # We use abs() to measure the size of the candle regardless of if it was red or green
    past_bodies = abs(df['close'].iloc[-11:-1] - df['open'].iloc[-11:-1])
    avg_body_size = past_bodies.mean()

    # Prevent divide-by-zero errors if the stock has been totally flat
    if avg_body_size < 0.01: 
        avg_body_size = 0.01 

    # The Math: Is this candle at least 3x bigger than the recent average?
    is_abnormal = current_body_size > (avg_body_size * 3)

    # The Safety Filters (Volume & Wicks)
    meets_volume = df['volume'].iloc[-1] >= 50000
    
    high_price = df['high'].iloc[-1]
    low_price = df['low'].iloc[-1]
    total_range = high_price - low_price
    
    strong_close = False
    if total_range > 0:
        close_percentile = (current_close - low_price) / total_range
        strong_close = close_percentile >= 0.70 # Must close in the top 30% (no giant wicks)

    # The Trigger
    if is_abnormal and meets_volume and strong_close:
        multiplier = current_body_size / avg_body_size
        print_alert(f"MID-MORNING ANOMALY ({multiplier:.1f}x SIZE)", symbol, current_close)

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

    current_time = datetime.now()
    
    # 1. THE OPEN: 9:30 to 9:37
    if current_time.hour == 9 and 30 <= current_time.minute <= 37:
        check_930_momentum(symbol, df)
        
    # 2. THE DOWNTIME: 9:38 to 10:29
    elif (current_time.hour == 9 and current_time.minute > 37) or (current_time.hour == 10 and current_time.minute < 30):
        check_downtime_anomaly(symbol, df)
        
    # 3. THE VELOCITY SHIFT: 10:30 to Close
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