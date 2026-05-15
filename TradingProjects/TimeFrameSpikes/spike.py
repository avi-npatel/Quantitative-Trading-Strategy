import asyncio
from alpaca.data.live import StockDataStream
from datetime import datetime
import pandas as pd
import pytz

# Initialize Alpaca Stream 
API_KEY = 'PKPWEEHLY7PXLM2LMCI6WOF43A'
SECRET_KEY = 'D5ZEcn71xiMJyhTiWkruhuJBo5bSvcveYc2mgVmYV2L8'
stream = StockDataStream(API_KEY, SECRET_KEY)

# Format: {'AAPL': {'open': [...], 'high': [...], 'low': [...], 'close': [...], 'volume': [...]}}
market_data = {}

# Constants for our strategy
MAX_PRICE = 40.00 
MIN_PRICE = 1.00

def check_930_momentum(symbol, df):
    """Optimized 9:30 AM logic: 3-min climb, surging volume, and anti-wick trap filter"""
    if len(df) < 3: return
    
    climbing = df['close'].iloc[-1] > df['close'].iloc[-2] > df['close'].iloc[-3]
    dropping = df['close'].iloc[-1] < df['close'].iloc[-2] < df['close'].iloc[-3]
    
    current_vol = df['volume'].iloc[-1]
    minute_1_vol = df['volume'].iloc[-3]
    min_volume = 50000 
    surge_factor = 1.5 
    
    volume_is_strong = (current_vol >= min_volume) and (current_vol > minute_1_vol * surge_factor)
    
    open_price = df['open'].iloc[-1]
    close_price = df['close'].iloc[-1]
    high_price = df['high'].iloc[-1]
    low_price = df['low'].iloc[-1]
    
    total_range = high_price - low_price
    if total_range == 0: return 
    
    close_percentile = (close_price - low_price) / total_range
    
    bullish_no_trap = close_percentile >= 0.70
    bearish_no_trap = close_percentile <= 0.30
    
    if climbing and volume_is_strong and bullish_no_trap:
        print_alert("9:30 AM BULL BREAKOUT (STRONG CLOSE)", symbol, close_price)
        
    elif dropping and volume_is_strong and bearish_no_trap:
        print_alert("9:30 AM BEAR DROPDOWN (STRONG CLOSE)", symbol, close_price)


def check_1030_velocity(symbol, df):
    """Looks for a sudden violent spike in price and volume at exactly 10:30 AM"""
    if len(df) < 10: return 
    
    current_close = df['close'].iloc[-1]
    previous_close = df['close'].iloc[-2]
    current_vol = df['volume'].iloc[-1]
    
    avg_vol_10m = df['volume'].iloc[-11:-1].mean()
    
    pct_change = ((current_close - previous_close) / previous_close) * 100
    
    if pct_change >= 1.5 and current_vol > (avg_vol_10m * 3):
        print_alert("10:30 AM UPSIDE VELOCITY SPIKE", symbol, current_close)
        
    elif pct_change <= -1.5 and current_vol > (avg_vol_10m * 3):
        print_alert("10:30 AM DOWNSIDE VELOCITY SPIKE", symbol, current_close)


def check_downtime_anomaly(symbol, df):
    """Catches sudden, abnormally large green candles during the mid-morning lull"""
    if len(df) < 11: return 

    current_open = df['open'].iloc[-1]
    current_close = df['close'].iloc[-1]
    
    if current_close <= current_open: return 

    current_body_size = current_close - current_open

    past_bodies = abs(df['close'].iloc[-11:-1] - df['open'].iloc[-11:-1])
    avg_body_size = past_bodies.mean()

    if avg_body_size < 0.01: 
        avg_body_size = 0.01 

    is_abnormal = current_body_size > (avg_body_size * 3)

    meets_volume = df['volume'].iloc[-1] >= 50000
    
    high_price = df['high'].iloc[-1]
    low_price = df['low'].iloc[-1]
    total_range = high_price - low_price
    
    strong_close = False
    if total_range > 0:
        close_percentile = (current_close - low_price) / total_range
        strong_close = close_percentile >= 0.70 

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
    
    if not (MIN_PRICE <= close_price <= MAX_PRICE):
        return

    # Initialize ticker in our dictionary with OHLCV structure
    if symbol not in market_data:
        market_data[symbol] = {'open': [], 'high': [], 'low': [], 'close': [], 'volume': []}
        
    # Append new data for all columns
    market_data[symbol]['open'].append(bar.open)
    market_data[symbol]['high'].append(bar.high)
    market_data[symbol]['low'].append(bar.low)
    market_data[symbol]['close'].append(bar.close)
    market_data[symbol]['volume'].append(bar.volume)
    
    # Keep only the last 15 minutes to save memory
    market_data[symbol]['open'] = market_data[symbol]['open'][-15:]
    market_data[symbol]['high'] = market_data[symbol]['high'][-15:]
    market_data[symbol]['low'] = market_data[symbol]['low'][-15:]
    market_data[symbol]['close'] = market_data[symbol]['close'][-15:]
    market_data[symbol]['volume'] = market_data[symbol]['volume'][-15:]

    df = pd.DataFrame(market_data[symbol])
    
    # ---------------------------------------------------------
    # TIME ROUTER: Convert Alpaca's UTC timestamp to US/Eastern
    # ---------------------------------------------------------
    bar_time_est = bar.timestamp.astimezone(pytz.timezone('US/Eastern'))
    h = bar_time_est.hour
    m = bar_time_est.minute
    
    # 0. THE SNIPER: Exactly 9:30 AM (Looks at the very first candle)
    if h == 9 and m == 30:
        c_open = bar.open
        c_close = bar.close
        change_pct = ((c_close - c_open) / c_open) * 100
        
        if abs(change_pct) >= 1.5:
            color = "🟢 GREEN" if change_pct > 0 else "🔴 RED"
            action = "BUY" if change_pct > 0 else "SHORT"
            print(f"\n[09:30:00 AM] 🔥 1.5% OPENING SPICE DETECTED")
            print(f"Ticker:        {symbol}")
            print(f"Price:         ${c_close:.2f}")
            print(f"Body Change:   {abs(change_pct):.2f}%")
            print(f"Candle Color:  {color}")
            print(f"Action:        {action}")
            print(f"Chart:         https://www.tradingview.com/chart/?symbol={symbol}")
            print("-" * 60)

    # 1. THE OPEN: 9:30 to 9:37 (Pulse-Seeker 3-Candle Logic)
    if h == 9 and 30 <= m <= 37:
        check_930_momentum(symbol, df)
        
    # 2. THE DOWNTIME: 9:38 to 10:29 (Anomaly Scanner)
    elif (h == 9 and m >= 38) or (h == 10 and m < 30):
        check_downtime_anomaly(symbol, df)
        
    # 3. THE VELOCITY SHIFT: 10:30 to Close (Velocity Scanner)
    elif (h == 10 and m >= 30) or h > 10:
        check_1030_velocity(symbol, df)
    
    # --- HEARTBEAT ---
    if symbol == 'SOFI': 
        print(f"[{bar_time_est.strftime('%H:%M:%S')}] Stream active... SOFI currently at ${close_price:.2f}")

# Subscribe to all minute bars
stream.subscribe_bars(handle_bar, '*')

# Start the live connection
print("Initializing Master Suite... Waiting for market data.")
stream.run()