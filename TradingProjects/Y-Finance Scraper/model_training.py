import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import precision_score, classification_report

def train_trading_model(csv_filename):
    df = pd.read_csv(csv_filename, index_col=0, parse_dates=True)
    
    df['Future_Close_5m'] = df['Close'].shift(-5)
    
    # Minimum profit margin of 0.03% to classify as a 'Buy'
    profit_threshold = 0.0003 
    df['Target'] = (df['Future_Close_5m'] > (df['Close'] * (1 + profit_threshold))).astype(int)
    df.dropna(inplace=True)

    features = ['Close', 'Volume', 'SMA_20', 'RSI_14', 'MACD', 'MACD_Hist', 'ROC_5']
    X = df[features]
    y = df['Target']
    
    split_index = int(len(df) * 0.8)
    X_train, X_test = X.iloc[:split_index], X.iloc[split_index:]
    y_train, y_test = y.iloc[:split_index], y.iloc[split_index:]
    
    # Increased the number of trees to handle the features
    model = RandomForestClassifier(n_estimators=200, max_depth=10, min_samples_split=20, random_state=42)
    model.fit(X_train, y_train)
    
    predictions = model.predict(X_test)
    precision = precision_score(y_test, predictions, zero_division=0)
    
    print("\n--- UPGRADED MODEL RESULTS ---")
    print(f"Model Precision: {precision * 100:.2f}%")
    
    # Number of Trades
    trades_taken = sum(predictions)
    print(f"Total 'Buy' signals generated on test data: {trades_taken}")

if __name__ == "__main__":
    FILE_NAME = "SPY_1m_features.csv" 
    train_trading_model(FILE_NAME)