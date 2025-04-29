import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import matplotlib.pyplot as plt
from groq import Groq

st.set_page_config(page_title="Crypto Technical and On-Chain Analysis", page_icon="📊")
st.title("Crypto Technical and On-Chain Analysis")

api_key = st.text_input("Enter your Groq API Key", type="password")

# --- Load and filter symbols ---
@st.cache_data(show_spinner="Loading trading pairs from Binance...")
def get_filtered_symbols():
    exchange = ccxt.bybit()
    markets = exchange.load_markets()
    filtered = sorted([s for s in markets.keys() if (s.endswith('/USDT') or s.endswith('/BTC')) and ':' not in s])
    return filtered

filtered_symbols = get_filtered_symbols()

symbol = st.selectbox("Select a /USDT or /BTC pair:", filtered_symbols, index=filtered_symbols.index("BTC/USDT") if "BTC/USDT" in filtered_symbols else 0)
timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w', '1M']
timeframe = st.selectbox("Select timeframe:", timeframes, index=timeframes.index('1d'))
limit = st.slider("Number of candles to fetch", min_value=30, max_value=500, value=90, step=10)

# --- Fetch OHLCV data ---
def fetch_ohlcv_ccxt(symbol, timeframe='1d', limit=90):
    exchange = ccxt.binance()
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return None
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    return df

# --- Multi-Timeframe Scan Function ---
def scan_timeframes_for_confluence(symbol, scan_timeframes, limit=90):
    exchange = ccxt.binance()
    results = []
    for tf in scan_timeframes:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            df['MA20'] = df['close'].rolling(window=20).mean()
            df['MA50'] = df['close'].rolling(window=50).mean()
            df['RSI'] = ta.rsi(df['close'], length=14)
            macd = ta.macd(df['close'])
            df['MACD'] = macd['MACD_12_26_9']
            # Trend
            trend = "uptrend" if df['MA20'][-1] > df['MA50'][-1] else "downtrend"
            # RSI
            rsi = df['RSI'][-1]
            rsi_signal = "overbought" if rsi > 70 else "oversold" if rsi < 30 else "neutral"
            # MACD
            macd_cross = "bullish" if df['MACD'][-1] > 0 else "bearish"
            # Price near Fibonacci (last 50 candles)
            lookback = min(50, len(df))
            recent_high = df['high'][-lookback:].max()
            recent_low = df['low'][-lookback:].min()
            fib_618 = recent_high - (recent_high - recent_low) * 0.618
            near_fib = abs(df['close'][-1] - fib_618) / df['close'][-1] < 0.01  # within 1%
            fib_signal = f"{fib_618:.4f}" + (" (near)" if near_fib else "")
            # Append results
            results.append({
                "Timeframe": tf,
                "Trend": trend,
                "RSI": f"{rsi:.2f} ({rsi_signal})",
                "MACD": macd_cross,
                "Fib 61.8%": fib_signal
            })
            # lookback = min(50, len(df))
            # recent_high = df['high'][-lookback:].max()
            # recent_low = df['low'][-lookback:].min()
            # fib_618 = recent_high - (recent_high - recent_low) * 0.618
            # near_fib = abs(df['close'][-1] - fib_618) / df['close'][-1] < 0.01  # within 1%
            # fib_signal = "near 61.8%" if near_fib else ""
            # # Append results
            # results.append({
            #     "Timeframe": tf,
            #     "Trend": trend,
            #     "RSI": f"{rsi:.2f} ({rsi_signal})",
            #     "MACD": macd_cross,
            #     "Fib 61.8%": fib_signal
            # })
        except Exception as e:
            results.append({
                "Timeframe": tf,
                "Trend": "N/A",
                "RSI": "N/A",
                "MACD": "N/A",
                "Fib 61.8%": "N/A"
            })
    return pd.DataFrame(results)

# --- Scan Button ---
if st.button("Scan for High-Probability Setups"):
    scan_timeframes = ['1d', '4h', '1h']
    with st.spinner("Scanning multiple timeframes..."):
        scan_results = scan_timeframes_for_confluence(symbol, scan_timeframes)
        st.write("### Multi-Timeframe Scan Results")
        st.table(scan_results)
        # Simple confluence logic: all uptrend or all downtrend
        if all(scan_results['Trend'] == "uptrend"):
            st.success("High-probability LONG setup: All timeframes in uptrend.")
        elif all(scan_results['Trend'] == "downtrend"):
            st.success("High-probability SHORT setup: All timeframes in downtrend.")
        else:
            st.info("No strong trend confluence detected. Await better alignment for higher probability.")

# --- Main Chart and AI Analysis ---
with st.spinner("Fetching price data..."):
    ohlcv = fetch_ohlcv_ccxt(symbol, timeframe, limit)
    if ohlcv is not None and not ohlcv.empty:
        latest_price = ohlcv['close'][-1]
        st.write(f"**Latest {symbol} Price:** {latest_price:,.6f}")
    else:
        st.stop()

# --- Technical indicators ---
ohlcv['MA20'] = ohlcv['close'].rolling(window=20).mean()
ohlcv['MA50'] = ohlcv['close'].rolling(window=50).mean()
ohlcv['RSI'] = ta.rsi(ohlcv['close'], length=14)
macd = ta.macd(ohlcv['close'])
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
ax.set_title(f"{symbol} Price Chart ({limit} candles, {timeframe})")
ax.set_ylabel("Price")
ax.legend()
st.pyplot(fig)

# --- Prepare data summary for AI ---
trend = "uptrend" if ohlcv['close'][-1] > ohlcv['close'][0] else "downtrend"
fib_str = "\n".join([f"{level}: {price:.6f}" for level, price in fib_levels.items()])
data_summary = f"""
Crypto Pair: {symbol}
Timeframe: {timeframe}
Latest Price: {latest_price:,.6f}
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
    user_prompt = f"""Here is the latest data for {symbol} on the {timeframe} timeframe:
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
