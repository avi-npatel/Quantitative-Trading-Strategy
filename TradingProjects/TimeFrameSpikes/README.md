Pulse-Seeker: Real-Time Momentum Scanner
Pulse-Seeker is a high-speed, algorithmic stock scanner built in Python. It connects directly to live market data via WebSockets to detect specific intraday momentum and velocity setups at key market times (9:30 AM and 10:30 AM).

Designed for small-cap and penny stock momentum trading (stocks under $40), it bypasses the standard 15-minute delays of free financial websites by utilizing the Alpaca Markets streaming API. When a setup is detected, it instantly outputs an alert to the terminal alongside a clickable TradingView chart link for rapid manual execution.

Core Trading Strategies
The scanner monitors a rolling 15-minute window of 1-minute candle data and executes two distinct time-locked strategies:

1. The 9:30 AM "Momentum Go" (9:30 AM - 9:35 AM)
This strategy captures sustained opening bell momentum, ignoring pre-market gaps.
The Logic: Looks for exactly 3 consecutive minutes of climbing closing prices (close3 > close2 > close1).
The Benefit: By focusing strictly on the step-ladder of closing prices, the algorithm naturally filters out minor intra-minute volatility (red candle fakeouts) while confirming the overarching structural trend is upwards.

2. The 10:30 AM "Velocity Spike" (10:30 AM Onwards)
This strategy hunts for sudden, violent explosions in price and volume after the morning chop has settled.
The Trigger: A single 1-minute candle moves > 1.5% from its open to its close.
The Volume Filter: The volume of that specific minute must be at least 3x higher than the average volume of the previous 10 minutes.
The Benefit: Ensures the price spike is backed by serious institutional or retail momentum, rather than just low-float manipulation.

Tech Stack
Language: Python 3
Live Data Feed: Alpaca Markets API (WebSockets)
Data Manipulation: pandas (For rapid rolling-average calculations and matrix filtering)

Setup & Installation
1. Clone the repository and navigate to the directory:
Bash
git clone https://github.com/yourusername/pulse-seeker.git
cd pulse-seeker

2. Install the required dependencies:
Bash
pip install alpaca-py pandas

3. Configure your API Keys:
You will need a free Alpaca account.
Log into your Alpaca Dashboard and navigate to Paper Trading.
Generate your Paper API keys.
Open the Python script and replace the placeholder variables at the top of the file:
Python
API_KEY = 'YOUR_PAPER_API_KEY'
SECRET_KEY = 'YOUR_PAPER_SECRET_KEY'

How to Use
Run the script directly from your terminal a few minutes before the market opens (e.g., 9:28 AM EST) to allow the WebSocket to connect and stabilize:
Bash
python spike.py

9:30 AM - 9:35 AM: The scanner will hunt for 3-minute momentum climbs.

9:36 AM - 10:29 AM: The scanner enters "Stealth Mode." It will stop printing but will silently build the 10-minute volume histories required for the next phase.

10:30 AM - Market Close: The scanner will continuously hunt for 1.5% / 3x Volume velocity spikes.

Heartbeat: A ping using a cheap stock (e.g., SOFI) will print to the console every 60 seconds to confirm the WebSocket connection is actively receiving data.

When an alert triggers, click the provided TradingView link in the terminal to instantly view the chart and execute your manual trade.