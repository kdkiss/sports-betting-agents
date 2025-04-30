import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import matplotlib.pyplot as plt
from groq import Groq
import warnings
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress pandas_ta warnings
warnings.filterwarnings("ignore", category=SyntaxWarning)
warnings.filterwarnings("ignore", message=r"invalid escape sequence '\\g'")
warnings.filterwarnings("ignore", message="There is no candle pattern named")

st.set_page_config(page_title="Crypto Technical and On-Chain Analysis", page_icon="📊")
st.title("Crypto Technical and On-Chain Analysis")

api_key = st.text_input("Enter your Groq API Key", type="password")

# --- Load and filter symbols ---
@st.cache_data(show_spinner="Loading trading pairs from Kraken...")
def get_filtered_symbols():
    try:
        exchange = ccxt.kraken({'enableRateLimit': True})
        markets = exchange.load_markets()
        filtered = sorted([s for s in markets.keys() if (s.endswith('/USDT') or s.endswith('/BTC')) and ':' not in s])
        return filtered
    except Exception as e:
        st.error(f"Error loading trading pairs: {e}")
        return []

filtered_symbols = get_filtered_symbols()
if not filtered_symbols:
    st.stop()

symbol = st.selectbox("Select a /USDT or /BTC pair:", filtered_symbols, index=filtered_symbols.index("BTC/USDT") if "BTC/USDT" in filtered_symbols else 0)
timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w', '1M']
timeframe = st.selectbox("Select timeframe:", timeframes, index=timeframes.index('1d'))
limit = st.slider("Number of candles to fetch", min_value=30, max_value=500, value=90, step=10)

# --- Fetch OHLCV data ---
@st.cache_data(show_spinner="Fetching price data...")
def fetch_ohlcv_ccxt(symbol, timeframe='1d', limit=90):
    exchange = ccxt.kraken({'enableRateLimit': True})
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        if not ohlcv:
            raise ValueError("No data returned from Kraken API")
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        return df
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return None

# --- Multi-Timeframe Scan Function ---
def scan_timeframes_for_confluence(symbol, scan_timeframes, limit=90):
    exchange = ccxt.kraken({'enableRateLimit': True})
    results = []
    risk_management_data = []
    scores = {'1d': 0.5, '4h': 0.3, '1h': 0.2}
    confluence_score = 0
    for tf in scan_timeframes:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=limit)
            logger.info(f"Raw OHLCV data for {tf} (first 5 rows): {ohlcv[:5]}")
            logger.info(f"Number of candles fetched for {tf}: {len(ohlcv)}")
            if not ohlcv or len(ohlcv) < 50:
                raise ValueError(f"Insufficient data for timeframe {tf}: {len(ohlcv)} candles")
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            if not all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume']):
                raise ValueError(f"Missing required columns in OHLCV data for {tf}")

            # Indicators
            df['MA20'] = df['close'].rolling(window=20).mean()
            df['MA50'] = df['close'].rolling(window=50).mean()
            df['RSI'] = ta.rsi(df['close'], length=14)
            macd = ta.macd(df['close'])
            df['MACD'] = macd['MACD_12_26_9']
            df['MACDh'] = macd['MACDh_12_26_9']
            bb = ta.bbands(df['close'], length=20, std=2)
            df['BB_upper'] = bb['BBU_20_2.0']
            df['BB_lower'] = bb['BBL_20_2.0']
            stoch = ta.stoch(df['high'], df['low'], df['close'], k=14, d=3)
            df['Stoch_K'] = stoch['STOCHk_14_3_3']
            df['Volume_MA10'] = df['volume'].rolling(window=10).mean()
            df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=14)

            # Signals
            trend_score = 1 if df['MA20'].iloc[-1] > df['MA50'].iloc[-1] else -1
            rsi = df['RSI'].iloc[-1]
            rsi_score = 1 if 30 < rsi < 70 else (-1 if rsi > 70 or rsi < 30 else 0)
            macd_score = 1 if df['MACDh'].iloc[-1] > 0 and df['MACD'].iloc[-1] > 0 else -1
            bb_signal = "near upper" if abs(df['close'].iloc[-1] - df['BB_upper'].iloc[-1]) / df['close'].iloc[-1] < 0.02 else \
                        "near lower" if abs(df['close'].iloc[-1] - df['BB_lower'].iloc[-1]) / df['close'].iloc[-1] < 0.02 else "neutral"
            bb_score = -0.5 if bb_signal == "near upper" else 0.5 if bb_signal == "near lower" else 0
            stoch_signal = "overbought" if df['Stoch_K'].iloc[-1] > 80 else "oversold" if df['Stoch_K'].iloc[-1] < 20 else "neutral"
            stoch_score = -0.5 if stoch_signal == "overbought" else 0.5 if stoch_signal == "oversold" else 0
            volume_signal = "strong" if df['volume'].iloc[-1] > df['Volume_MA10'].iloc[-1] * 1.5 else "weak"
            volume_score = 0.5 if volume_signal == "strong" else -0.5

            # Fibonacci proximity
            lookback = min(50, len(df))
            recent_high = df['high'][-lookback:].max()
            recent_low = df['low'][-lookback:].min()
            fib_618 = recent_high - (recent_high - recent_low) * 0.618
            near_fib = abs(df['close'].iloc[-1] - fib_618) / df['close'].iloc[-1] < 0.02
            fib_score = 0.5 if near_fib else 0

            # Candlestick patterns
            candle_patterns = ta.cdl_pattern(df['open'], df['high'], df['low'], df['close'], 
                                           name=['doji', 'engulfing', 'hammer', 'invertedhammer'])
            logger.info(f"Candlestick patterns result for {tf}: {candle_patterns if candle_patterns is not None else 'None'}")
            
            bullish_pattern = False
            bearish_pattern = False
            pattern_score = 0
            
            if candle_patterns is not None:
                logger.info(f"Candlestick patterns columns for {tf}: {candle_patterns.columns.tolist()}")
                # Check for patterns using the actual column names
                for col in candle_patterns.columns:
                    if 'CDL_HAMMER' in col and candle_patterns[col].iloc[-1] > 0:
                        bullish_pattern = True
                    elif 'CDL_ENGULFING' in col and candle_patterns[col].iloc[-1] > 0:
                        bullish_pattern = True
                    elif 'CDL_ENGULFING' in col and candle_patterns[col].iloc[-1] < 0:
                        bearish_pattern = True
            else:
                logger.info(f"No candlestick patterns detected for {tf}")

            pattern_score = 0.5 if bullish_pattern else (-0.5 if bearish_pattern else 0)

            # Risk management
            stop_loss_long = df['close'].iloc[-1] - 2 * df['ATR'].iloc[-1]
            take_profit_long = df['close'].iloc[-1] + 3 * df['ATR'].iloc[-1]
            stop_loss_short = df['close'].iloc[-1] + 2 * df['ATR'].iloc[-1]
            take_profit_short = df['close'].iloc[-1] - 3 * df['ATR'].iloc[-1]

            # Total score for this timeframe
            tf_score = (trend_score + rsi_score + macd_score + bb_score + stoch_score + volume_score + fib_score + pattern_score) * scores.get(tf, 0.1)
            confluence_score += tf_score

            # Base result dictionary
            result = {
                "Timeframe": tf,
                "Trend": "uptrend" if trend_score > 0 else "downtrend",
                "RSI": f"{rsi:.2f} ({'overbought' if rsi > 70 else 'oversold' if rsi < 30 else 'neutral'})",
                "Volume": volume_signal,
                "Candle Pattern": "Bullish" if bullish_pattern else "Bearish" if bearish_pattern else "None",
                "Fib 61.8%": f"{fib_618:.4f}" + (" (near)" if near_fib else "")
            }

            risk_management = {
                "Stop Loss (Long)": f"{stop_loss_long:.4f}",
                "Take Profit (Long)": f"{take_profit_long:.4f}",
                "Stop Loss (Short)": f"{stop_loss_short:.4f}",
                "Take Profit (Short)": f"{take_profit_short:.4f}"
            }

            results.append(result)
            risk_management_data.append(risk_management)

        except Exception as e:
            logger.error(f"Error in scan for {tf}: {e}")
            result = {
                "Timeframe": tf,
                "Trend": "N/A",
                "RSI": "N/A",
                "Volume": "N/A",
                "Candle Pattern": "N/A",
                "Fib 61.8%": "N/A"
            }
            risk_management = {
                "Stop Loss (Long)": "N/A",
                "Take Profit (Long)": "N/A",
                "Stop Loss (Short)": "N/A",
                "Take Profit (Short)": "N/A"
            }
            results.append(result)
            risk_management_data.append(risk_management)

    df_results = pd.DataFrame(results)
    signal = "Strong LONG" if confluence_score > 1.5 else "Strong SHORT" if confluence_score < -1.5 else "Neutral"
    
    if signal in ["Strong LONG", "Strong SHORT"]:
        for i in range(len(results)):
            results[i].update(risk_management_data[i])
        df_results = pd.DataFrame(results)
    
    return df_results, signal, confluence_score

# --- Scan Button ---
if st.button("Scan for High-Probability Setups"):
    scan_timeframes = ['1d', '4h', '1h']
    with st.spinner("Scanning multiple timeframes..."):
        scan_results, signal, score = scan_timeframes_for_confluence(symbol, scan_timeframes)
        st.write("### Multi-Timeframe Scan Results")
        st.table(scan_results)
        if score > 1.5:
            st.success(f"High-probability LONG setup (Score: {score:.2f})")
        elif score < -1.5:
            st.success(f"High-probability SHORT setup (Score: {score:.2f})")
        else:
            st.info(f"No strong setup detected (Score: {score:.2f})")

# --- Main Chart and AI Analysis ---
with st.spinner("Fetching price data..."):
    ohlcv = fetch_ohlcv_ccxt(symbol, timeframe, limit)
    if ohlcv is None or ohlcv.empty:
        st.stop()
    latest_price = ohlcv['close'].iloc[-1]
    st.write(f"**Latest {symbol} Price:** {latest_price:,.6f}")

# --- Technical indicators ---
ohlcv['MA20'] = ohlcv['close'].rolling(window=20).mean()
ohlcv['MA50'] = ohlcv['close'].rolling(window=50).mean()
ohlcv['RSI'] = ta.rsi(ohlcv['close'], length=14)
macd = ta.macd(ohlcv['close'])
ohlcv['MACD'] = macd['MACD_12_26_9']
ohlcv['MACDh'] = macd['MACDh_12_26_9']
ohlcv['MACDs'] = macd['MACDs_12_26_9']
bb = ta.bbands(ohlcv['close'], length=20, std=2)
ohlcv['BB_upper'] = bb['BBU_20_2.0']
ohlcv['BB_lower'] = bb['BBL_20_2.0']
ohlcv['BB_mid'] = bb['BBM_20_2.0']
stoch = ta.stoch(ohlcv['high'], ohlcv['low'], ohlcv['close'], k=14, d=3)
ohlcv['Stoch_K'] = stoch['STOCHk_14_3_3']
ohlcv['Stoch_D'] = stoch['STOCHd_14_3_3']
ohlcv['Volume_MA10'] = ohlcv['volume'].rolling(window=10).mean()
ohlcv['ATR'] = ta.atr(ohlcv['high'], ohlcv['low'], ohlcv['close'], length=14)

# --- Fibonacci Calculation ---
lookback = min(50, len(ohlcv))
recent_high = ohlcv['high'][-lookback:].max()
recent_low = ohlcv['low'][-lookback:].min()
fib_ratios = [0.236, 0.382, 0.5, 0.618, 0.786]
fib_levels = {f"{int(r*100)}%": recent_high - (recent_high - recent_low) * r for r in fib_ratios}
fib_levels['0%'] = recent_high
fib_levels['100%'] = recent_low
fib_df = pd.DataFrame(list(fib_levels.items()), columns=['Level', 'Price']).sort_values('Price', ascending=False)

# --- Show indicators and Fibonacci ---
st.write("#### Key Technical Indicators (latest values)")
st.table(ohlcv[['close', 'MA20', 'MA50', 'RSI', 'MACD', 'Stoch_K', 'Stoch_D', 'BB_upper', 'BB_lower', 'ATR', 'volume']].tail(1).T)

st.write(f"#### Fibonacci Retracement Levels (last {lookback} candles)")
st.table(fib_df)

# --- Display chart ---
fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 8), gridspec_kw={'height_ratios': [3, 1, 1]})
ohlcv['close'].plot(ax=ax1, label='Close', color='blue')
if ohlcv['MA20'].notnull().any():
    ohlcv['MA20'].plot(ax=ax1, label='MA20', color='orange')
if ohlcv['MA50'].notnull().any():
    ohlcv['MA50'].plot(ax=ax1, label='MA50', color='green')
if ohlcv['BB_upper'].notnull().any():
    ohlcv['BB_upper'].plot(ax=ax1, label='BB Upper', color='red', linestyle='--')
    ohlcv['BB_lower'].plot(ax=ax1, label='BB Lower', color='red', linestyle='--')
for level, price in fib_levels.items():
    ax1.axhline(price, linestyle='--', alpha=0.5, label=f'Fib {level}')
ax1.set_title(f"{symbol} Price Chart ({limit} candles, {timeframe})")
ax1.set_ylabel("Price")
ax1.legend()
ohlcv['RSI'].plot(ax=ax2, label='RSI', color='purple')
ax2.axhline(70, color='red', linestyle='--')
ax2.axhline(30, color='green', linestyle='--')
ax2.set_title("RSI (14)")
ax2.legend()
ohlcv['MACD'].plot(ax=ax3, label='MACD', color='blue')
ohlcv['MACDs'].plot(ax=ax3, label='Signal', color='orange')
ax3.bar(ohlcv.index, ohlcv['MACDh'], color='gray', alpha=0.3, label='Histogram')
ax3.set_title("MACD")
ax3.legend()
plt.tight_layout()
st.pyplot(fig)

# --- Prepare data summary for AI ---
trend = "uptrend" if ohlcv['close'].iloc[-1] > ohlcv['close'].iloc[0] else "downtrend"
fib_str = "\n".join([f"{level}: {price:.6f}" for level, price in fib_levels.items()])
data_summary = f"""
Crypto Pair: {symbol}
Timeframe: {timeframe}
Latest Price: {latest_price:,.6f}
20-period MA: {ohlcv['MA20'].iloc[-1]:,.6f}
50-period MA: {ohlcv['MA50'].iloc[-1]:,.6f}
RSI (14): {ohlcv['RSI'].iloc[-1]:.2f}
Stochastic K/D: {ohlcv['Stoch_K'].iloc[-1]:.2f}/{ohlcv['Stoch_D'].iloc[-1]:.2f}
MACD: {ohlcv['MACD'].iloc[-1]:.4f}
Bollinger Bands: Upper={ohlcv['BB_upper'].iloc[-1]:.4f}, Lower={ohlcv['BB_lower'].iloc[-1]:.4f}
ATR (14): {ohlcv['ATR'].iloc[-1]:.4f}
Latest Volume: {ohlcv['volume'].iloc[-1]:,.2f}
Volume Trend: {'Above' if ohlcv['volume'].iloc[-1] > ohlcv['Volume_MA10'].iloc[-1] else 'Below'} 10-period MA
Recent Price Trend: {trend}
Fibonacci Retracement Levels (last {lookback} candles):
{fib_str}
"""

# --- Groq AI Analysis ---
if api_key and st.button("Generate AI Analysis"):
    try:
        client = Groq(api_key=api_key)
        system_prompt = """
You are a highly skilled Crypto Technical and On-Chain Analyst. Using the provided real-time price, technical indicator data, volume, and Fibonacci retracement levels, generate a comprehensive analysis including:

- Pattern recognition (mention any likely patterns based on recent price action)
- Candlestick and trend analysis
- Support/resistance levels (use recent highs/lows and Fibonacci)
- Indicator analysis (interpret RSI, MA, MACD, Stochastic Oscillator, Bollinger Bands, and ATR values)
- Volume analysis (comment on current volume vs. 10-period moving average)
- Fibonacci retracement analysis (explain the significance of levels and where price is relative to them)
- Risk management suggestions (suggest stop-loss and take-profit levels based on ATR and Fibonacci)
- Actionable insights for traders and investors

Format your answer as a structured technical analysis summary.
"""
        user_prompt = f"""Here is the latest data for {symbol} on the {timeframe} timeframe:
{data_summary}
Please provide a detailed technical analysis and actionable recommendations."""
        with st.spinner("Analyzing with AI..."):
            response = client.chat.completions.create(
                model="meta-llama/llama-4-maverick-17b-128e-instruct",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=2000,
                temperature=0.2
            )
            analysis = response.choices[0].message.content
            st.write("### Technical Analysis Summary")
            st.write(analysis)
    except Exception as e:
        st.error(f"Error generating AI analysis: {e}")
