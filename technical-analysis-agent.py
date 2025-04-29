import streamlit as st
import requests
import pandas as pd
import pandas_ta as ta
import matplotlib.pyplot as plt
from groq import Groq

st.set_page_config(page_title="Crypto Technical and On-Chain Analysis", page_icon="📊")
st.title("Crypto Technical and On-Chain Analysis")

api_key = st.text_input("Enter your Groq API Key", type="password")

# --- Load and filter symbols using CoinGecko ---
@st.cache_data(show_spinner="Loading supported coins from CoinGecko...")
def get_coins():
    url = "https://api.coingecko.com/api/v3/coins/list"
    r = requests.get(url)
    coins = r.json()
    # Only keep major coins for usability
    coins = [c for c in coins if c['symbol'].upper() in [
        'BTC', 'ETH', 'BNB', 'SOL', 'ADA', 'XRP', 'DOGE', 'AVAX', 'DOT', 'MATIC', 'LINK', 'SHIB', 'TRX', 'LTC', 'BCH', 'UNI', 'ATOM', 'FIL', 'ETC', 'ICP', 'APT'
    ]]
    return {f"{c['symbol'].upper()} / {c['id']}": c['id'] for c in coins}

coin_map = get_coins()
coin_choices = list(coin_map.keys())
symbol = st.selectbox("Select a coin:", coin_choices, index=coin_choices.index("BTC / bitcoin") if "BTC / bitcoin" in coin_choices else 0)
coin_id = coin_map[symbol]

# --- Timeframe selection (CoinGecko supports: 1, 7, 14, 30, 90, 180, 365, max days) ---
timeframes = {
    "1d": 1, "7d": 7, "14d": 14, "30d": 30, "90d": 90, "180d": 180, "1y": 365, "max": "max"
}
tf_label = st.selectbox("Select timeframe:", list(timeframes.keys()), index=1)
days = timeframes[tf_label]

# --- Fetch OHLCV data from CoinGecko ---
@st.cache_data(show_spinner="Fetching OHLCV data...")
def fetch_ohlcv_coingecko(coin_id, days):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    params = {"vs_currency": "usd", "days": days, "interval": "daily"}
    r = requests.get(url, params=params)
    if r.status_code != 200:
        return None
    data = r.json()
    # CoinGecko returns [timestamp, price] for prices, [timestamp, volume] for volumes
    prices = data.get("prices", [])
    volumes = {x[0]: x[1] for x in data.get("total_volumes", [])}
    # Approximate OHLC from prices (CoinGecko free API doesn't provide true OHLC)
    ohlc = []
    for i, (ts, price) in enumerate(prices):
        ohlc.append([ts, price, price, price, price])  # open, high, low, close all = price
    df = pd.DataFrame(ohlc, columns=["timestamp", "open", "high", "low", "close"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    df["volume"] = df.index.map(lambda x: volumes.get(int(x.timestamp() * 1000), None))
    return df

ohlcv = fetch_ohlcv_coingecko(coin_id, days)
if ohlcv is None or ohlcv.empty:
    st.error("Failed to fetch data from CoinGecko.")
    st.stop()

# --- Technical indicators ---
ohlcv['MA20'] = ohlcv['close'].rolling(window=20).mean()
ohlcv['MA50'] = ohlcv['close'].rolling(window=50).mean()
ohlcv['RSI'] = ta.rsi(ohlcv['close'], length=14)
macd = ta.macd(ohlcv['close'])
if isinstance(macd, pd.DataFrame) and macd.shape[1] >= 3:
    ohlcv['MACD'] = macd.iloc[:, 0]
    ohlcv['MACDh'] = macd.iloc[:, 1]
    ohlcv['MACDs'] = macd.iloc[:, 2]
else:
    ohlcv['MACD'] = ohlcv['MACDh'] = ohlcv['MACDs'] = pd.NA
ohlcv['MACD'] = macd['MACD_12_26_9']
ohlcv['MACDh'] = macd['MACDh_12_26_9']
ohlcv['MACDs'] = macd['MACDs_12_26_9']

# --- Fibonacci Calculation (last 50 candles or less) ---
lookback = min(50, len(ohlcv))
recent_high = ohlcv['high'][-lookback:].max()
recent_low = ohlcv['low'][-lookback:].min()
fib_ratios = [0.236, 0.382, 0.5, 0.618, 0.786]
fib_levels = {f"{int(r*100)}%": recent_high - (recent_high - recent_low) * r for r in fib_ratios}
fib_levels['0%'] = recent_high
fib_levels['100%'] = recent_low
fib_df = pd.DataFrame(list(fib_levels.items()), columns=['Level', 'Price']).sort_values('Price', ascending=False)

# --- Show indicators and Fibonacci in Streamlit ---
st.write("#### Key Technical Indicators (latest values)")
st.table(ohlcv[['close', 'MA20', 'MA50', 'RSI', 'MACD', 'volume']].tail(1).T)

st.write(f"#### Fibonacci Retracement Levels (last {lookback} candles)")
st.table(fib_df)

# --- Display chart ---
fig, ax = plt.subplots(figsize=(10,5))
ohlcv['close'].plot(ax=ax, label='Close', color='blue')
if ohlcv['MA20'].notnull().any():
    ohlcv['MA20'].plot(ax=ax, label='MA20', color='orange')
if ohlcv['MA50'].notnull().any():
    ohlcv['MA50'].plot(ax=ax, label='MA50', color='green')
ax.set_title(f"{symbol} Price Chart ({days} days)")
ax.set_ylabel("Price")
ax.legend()
st.pyplot(fig)

# --- Prepare data summary for AI ---
trend = "uptrend" if ohlcv['close'][-1] > ohlcv['close'][0] else "downtrend"
fib_str = "\n".join([f"{level}: {price:.6f}" for level, price in fib_levels.items()])
data_summary = f"""
Crypto Pair: {symbol}
Timeframe: {tf_label}
Latest Price: {ohlcv['close'][-1]:,.6f}
20-period MA: {ohlcv['MA20'][-1]:,.6f}
50-period MA: {ohlcv['MA50'][-1]:,.6f}
RSI (14): {ohlcv['RSI'][-1]:.2f}
MACD: {ohlcv['MACD'][-1]:.4f}
Latest Volume: {ohlcv['volume'][-1]:,.2f}
Recent Price Trend: {trend}
Fibonacci Retracement Levels (last {lookback} candles):
{fib_str}
"""

# --- Groq AI Analysis ---
if api_key and st.button("Generate AI Analysis"):
    client = Groq(api_key=api_key)
    system_prompt = """
You are a highly skilled Crypto Technical and On-Chain Analyst. Using the provided real-time price, technical indicator data, volume, and Fibonacci retracement levels, generate a comprehensive analysis including:

- Pattern recognition (mention any likely patterns based on recent price action)
- Candlestick and trend analysis
- Support/resistance levels (use recent highs/lows and Fibonacci)
- Indicator analysis (interpret RSI, MA, MACD values)
- Volume analysis (comment on current volume vs. recent history)
- Fibonacci retracement analysis (explain the significance of levels and where price is relative to them)
- Risk management suggestions
- Actionable insights for traders and investors

Format your answer as a structured technical analysis summary.
"""
    user_prompt = f"""Here is the latest data for {symbol} on the {tf_label} timeframe:
{data_summary}
Please provide a detailed technical analysis and actionable recommendations."""
    with st.spinner("Analyzing with AI..."):
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=1000,
            temperature=0.2
        )
        analysis = response.choices[0].message.content
        st.write("### Technical Analysis Summary")
        st.write(analysis)
