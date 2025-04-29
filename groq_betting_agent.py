import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
from groq import Groq

st.set_page_config(page_title="AI Sports Betting Agent", page_icon="⚽")
st.title("AI Sports Betting Agent")

# groq_api_key = st.text_input("Enter your Groq API Key", type="password")
# odds_api_key = st.text_input("Enter your The Odds API Key", type="password")
groq_api_key = "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"
odds_api_key = "dc7a3805b6241b1b9d3b9827fceafcfa"

# --- Fetch available sports ---
@st.cache_data
def get_sports(api_key):
    url = f"https://api.the-odds-api.com/v4/sports/?apiKey={api_key}"
    r = requests.get(url)
    if r.status_code != 200:
        return []
    return r.json()

if odds_api_key:
    sports = get_sports(odds_api_key)
    sport_names = [s['title'] for s in sports]
    sport_keys = {s['title']: s['key'] for s in sports}
    selected_sport = st.selectbox("Select a sport:", sport_names)
    selected_sport_key = sport_keys[selected_sport]
else:
    st.warning("Enter your The Odds API key to load sports.")
    st.stop()

# --- Fetch upcoming events ---
@st.cache_data
def get_odds(api_key, sport_key):
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={api_key}&regions=eu&markets=h2h"
    r = requests.get(url)
    if r.status_code != 200:
        return []
    return r.json()

events = get_odds(odds_api_key, selected_sport_key)
if not events:
    st.warning("No events found or API limit reached.")
    st.stop()

event_names = [f"{e['home_team']} vs {e['away_team']}" for e in events]
selected_event_index = st.selectbox("Select a match:", range(len(event_names)), format_func=lambda i: event_names[i])
selected_event = events[selected_event_index]

# --- Display odds table ---
st.write("### Odds")
odds_data = []
for bookmaker in selected_event.get('bookmakers', []):
    for market in bookmaker.get('markets', []):
        if market['key'] == 'h2h':
            for outcome in market['outcomes']:
                odds_data.append({
                    'Bookmaker': bookmaker['title'],
                    'Team': outcome['name'],
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
        if market['key'] == 'h2h':
            for outcome in market['outcomes']:
                match_summary += f"\n  {outcome['name']}: {outcome['price']}"

# --- AI Analysis ---
if groq_api_key and st.button("Generate AI Betting Analysis"):
    client = Groq(api_key=groq_api_key)
    system_prompt = """
You are an expert sports betting analyst. Using the provided odds and match data, analyze the match, discuss potential value bets, risk factors, and provide actionable betting recommendations. Consider recent form, head-to-head, and market odds. Format your answer as a structured betting analysis.
"""
    user_prompt = f"""Here is the latest data for the match:
{match_summary}
Please provide a detailed betting analysis and recommendations."""
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
        st.write("### AI Betting Analysis")
        st.write(analysis)
