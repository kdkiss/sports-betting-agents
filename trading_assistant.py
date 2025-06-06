import streamlit as st
import pandas as pd
import yfinance as yf
from groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

st.set_page_config(page_title="Trading Assistant", page_icon="📈")
st.title("Trading Assistant")

st.write(
    "Enter a comma-separated list of stock symbols to fetch recent price data "
    "and get AI-generated trade suggestions."
)

symbols_input = st.text_input("Tickers (e.g. AAPL, MSFT, GOOGL)")
period = st.selectbox("History Period", ["1mo", "3mo", "6mo", "1y"], index=0)

if st.button("Analyze") and symbols_input:
    tickers = [s.strip().upper() for s in symbols_input.split(",") if s.strip()]
    all_prices = []
    for ticker in tickers:
        data = yf.Ticker(ticker).history(period=period)
        if data.empty:
            st.warning(f"No price data found for {ticker}")
            continue
        st.subheader(ticker)
        st.line_chart(data["Close"])
        last_price = data["Close"].iloc[-1]
        st.write(f"Latest close: {last_price:.2f}")
        all_prices.append((ticker, last_price))

    if GROQ_API_KEY and all_prices:
        summary = "\n".join(f"{t}: {p:.2f}" for t, p in all_prices)
        client = Groq(api_key=GROQ_API_KEY)
        user_prompt = (
            "Provide short-term trading suggestions for the following tickers "
            f"based on recent price action:\n{summary}"
        )
        with st.spinner("Querying Groq..."):
            resp = client.chat.completions.create(
                model="meta-llama/llama-4-maverick-17b-128e-instruct",
                messages=[{"role": "user", "content": user_prompt}],
                max_tokens=800,
                temperature=0.3,
            )
        st.write("### AI Suggestions")
        st.write(resp.choices[0].message.content)
    elif not GROQ_API_KEY:
        st.info("Set GROQ_API_KEY in your environment to enable AI suggestions.")
