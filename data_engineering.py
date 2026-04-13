import yfinance as yf
import pandas as pd

def fetch_and_prep_data(ticker_symbol):
    print(f"Fetching 1-minute data for {ticker_symbol}...")
    df = yf.download(tickers=ticker_symbol, period="7d", interval="1m")
    
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    df.dropna(inplace=True)
    print("Calculating advanced features natively...")

    # Volatility: Bollinger Bands & SMA
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['STDEV_20'] = df['Close'].rolling(window=20).std()
    df['BBU_20'] = df['SMA_20'] + (df['STDEV_20'] * 2)
    df['BBL_20'] = df['SMA_20'] - (df['STDEV_20'] * 2)
    
    # Momentum: RSI
    delta = df['Close'].diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    loss = -delta.clip(upper=0).ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    rs = gain / loss
    df['RSI_14'] = 100 - (100 / (1 + rs))

    # Trend: MACD (12, 26, 9)
    df['EMA_12'] = df['Close'].ewm(span=12, adjust=False).mean()
    df['EMA_26'] = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = df['EMA_12'] - df['EMA_26']
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['MACD_Signal'] # The difference between MACD and Signal

    # Velocity: Rate of Change (ROC) over 5 minutes
    df['ROC_5'] = df['Close'].pct_change(periods=5) * 100

    df.dropna(inplace=True) 
    return df

if __name__ == "__main__":
    TICKER = "SPY" 
    historical_data = fetch_and_prep_data(TICKER)
    filename = f"{TICKER}_1m_features.csv"
    historical_data.to_csv(filename)
    print(f"\nSuccess! Upgraded Data shape: {historical_data.shape}")