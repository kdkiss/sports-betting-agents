import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
from groq import Groq
import os
from dotenv import load_dotenv


# Load environment variables from .env if present
load_dotenv()

ODDS_API_KEY = os.getenv("ODDS_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

st.set_page_config(page_title="AI Sports Betting Agent", page_icon="⚽")
st.title("AI Sports Betting Agent")

if not ODDS_API_KEY or not GROQ_API_KEY:
    st.error("API keys not found in environment variables. Please set ODDS_API_KEY and GROQ_API_KEY in your .env file or environment.")
    st.stop()

# --- Fetch available sports ---
@st.cache_data
def get_sports(api_key):
    url = f"https://api.the-odds-api.com/v4/sports/?apiKey={api_key}"
    r = requests.get(url)
    if r.status_code != 200:
        return []
    return r.json()

sports = get_sports(ODDS_API_KEY)
sport_names = [s['title'] for s in sports]
sport_keys = {s['title']: s['key'] for s in sports}
selected_sport = st.selectbox("Select a sport:", sport_names)
selected_sport_key = sport_keys[selected_sport]

# --- Market selection ---
market_options = {
    "Moneyline (h2h)": "h2h",
    "Point Spread (spreads)": "spreads",
    "Total (over/under)": "totals",
    "Outrights (futures)": "outrights"
}
selected_markets = st.multiselect(
    "Select odds markets to display:",
    options=list(market_options.keys()),
    default=["Moneyline (h2h)"]
)
selected_market_keys = [market_options[m] for m in selected_markets]
markets_param = ",".join(selected_market_keys)

# --- Fetch upcoming events with selected markets ---
@st.cache_data
def get_odds(api_key, sport_key, markets):
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={api_key}&regions=eu&markets={markets}"
    r = requests.get(url)
    if r.status_code != 200:
        return []
    return r.json()

events = get_odds(ODDS_API_KEY, selected_sport_key, markets_param)
if not events:
    st.warning("No events found or API limit reached.")
    st.stop()

event_names = [f"{e['home_team']} vs {e['away_team']}" for e in events]
selected_event_index = st.selectbox("Select a match:", range(len(event_names)), format_func=lambda i: event_names[i])
selected_event = events[selected_event_index]

# --- Display odds table for all selected markets ---
st.write("### Odds")
odds_data = []
for bookmaker in selected_event.get('bookmakers', []):
    for market in bookmaker.get('markets', []):
        if market['key'] in selected_market_keys:
            for outcome in market['outcomes']:
                odds_data.append({
                    'Bookmaker': bookmaker['title'],
                    'Market': market['key'],
                    'Outcome': outcome['name'],
                    'Odds': outcome['price']
                })
odds_df = pd.DataFrame(odds_data)
st.table(odds_df)

# --- Prepare data summary for AI ---
match_summary = f"""
Match: {selected_event['home_team']} vs {selected_event['away_team']}
Sport: {selected_sport}
Odds:
"""
for bookmaker in selected_event.get('bookmakers', []):
    match_summary += f"\nBookmaker: {bookmaker['title']}"
    for market in bookmaker.get('markets', []):
        if market['key'] in selected_market_keys:
            match_summary += f"\n  Market: {market['key']}"
            for outcome in market['outcomes']:
                match_summary += f"\n    {outcome['name']}: {outcome['price']}"

# --- AI Analysis ---
if st.button("Generate AI Betting Analysis"):
    client = Groq(api_key=GROQ_API_KEY)
    system_prompt = """
You are a highly experienced sports betting analyst. Using the provided odds and match data, deliver a comprehensive, structured betting analysis that includes:

- **Match Overview:** Briefly summarize the key details of the match.  
- **Recent Form Analysis:** Evaluate the recent performances of both teams/players.  
- **Head-to-Head Comparison:** Highlight relevant historical results and trends.  
- **Odds & Market Assessment:** Analyze current market odds to identify discrepancies or potential value across all available bet types (e.g., match winner, totals/over-under, handicaps, props, etc.).  
- **Risk Factors:** Discuss uncertainties, injuries, lineup changes, or other factors that could influence the outcome.  
- **Value Bets & Recommendations:** Clearly identify any value bets across all markets, explain your reasoning, and provide actionable betting recommendations for each.  

Ensure your analysis is logical, data-driven, and easy to follow. Present your findings in a well-structured format with clear headings for each section.

"""
    user_prompt = f"""Here is the latest data for the match:
{match_summary}
Please provide a detailed betting analysis and recommendations."""
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
        st.write("### AI Betting Analysis")
        st.write(analysis)
