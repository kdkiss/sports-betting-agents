import streamlit as st
import requests
import pandas as pd
import os
from dotenv import load_dotenv
from groq import Groq

# Load environment variables
load_dotenv()
ODDS_API_KEY = os.getenv("ODDS_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
FOOTBALL_DATA_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")

st.set_page_config(page_title="AI Sports Betting Agent", page_icon="⚽")
st.title("AI Sports Betting Agent")

if not ODDS_API_KEY or not GROQ_API_KEY or not FOOTBALL_DATA_API_KEY:
    st.error("API keys not found in environment variables. Please set ODDS_API_KEY, GROQ_API_KEY, and FOOTBALL_DATA_API_KEY in your .env file or environment.")
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

# --- Fetch upcoming events ---
@st.cache_data
def get_odds(api_key, sport_key):
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={api_key}&regions=eu&markets=h2h"
    r = requests.get(url)
    if r.status_code != 200:
        return []
    return r.json()

events = get_odds(ODDS_API_KEY, selected_sport_key)
if not events:
    st.warning("No events found or API limit reached.")
    st.stop()

event_names = [f"{e['home_team']} vs {e['away_team']}" for e in events]
selected_event_index = st.selectbox("Select a match:", range(len(event_names)), format_func=lambda i: event_names[i])
selected_event = events[selected_event_index]
home_team = selected_event['home_team']
away_team = selected_event['away_team']

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

# --- Football-Data.org: Fetch recent matches and H2H ---
def get_team_id(team_name, api_key):
    url = f"https://api.football-data.org/v4/teams?name={team_name}"
    headers = {"X-Auth-Token": api_key}
    r = requests.get(url, headers=headers)
    if r.status_code != 200 or not r.json().get("teams"):
        return None
    return r.json()["teams"][0]["id"]

def get_team_form(team_id, api_key, n=5):
    url = f"https://api.football-data.org/v4/teams/{team_id}/matches?status=FINISHED&limit={n}"
    headers = {"X-Auth-Token": api_key}
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        return []
    matches = r.json().get("matches", [])
    form = []
    for m in matches:
        result = "W" if (m["score"]["winner"] == "HOME_TEAM" and m["homeTeam"]["id"] == team_id) or \
                        (m["score"]["winner"] == "AWAY_TEAM" and m["awayTeam"]["id"] == team_id) else "L" if m["score"]["winner"] != "DRAW" else "D"
        form.append(f"{m['homeTeam']['name']} {m['score']['fullTime']['home']} - {m['score']['fullTime']['away']} {m['awayTeam']['name']} ({result})")
    return form

def get_h2h(home_id, away_id, api_key, n=5):
    url = f"https://api.football-data.org/v4/teams/{home_id}/matches?status=FINISHED&limit=50"
    headers = {"X-Auth-Token": api_key}
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        return []
    matches = [m for m in r.json().get("matches", []) if m["awayTeam"]["id"] == away_id or m["homeTeam"]["id"] == away_id]
    return [f"{m['homeTeam']['name']} {m['score']['fullTime']['home']} - {m['score']['fullTime']['away']} {m['awayTeam']['name']}" for m in matches[:n]]

with st.spinner("Fetching team stats..."):
    home_id = get_team_id(home_team, FOOTBALL_DATA_API_KEY)
    away_id = get_team_id(away_team, FOOTBALL_DATA_API_KEY)
    home_form = get_team_form(home_id, FOOTBALL_DATA_API_KEY) if home_id else []
    away_form = get_team_form(away_id, FOOTBALL_DATA_API_KEY) if away_id else []
    h2h = get_h2h(home_id, away_id, FOOTBALL_DATA_API_KEY) if home_id and away_id else []

st.write(f"### {home_team} Recent Form")
st.write(home_form if home_form else "No data found.")

st.write(f"### {away_team} Recent Form")
st.write(away_form if away_form else "No data found.")

st.write("### Head-to-Head (last 5)")
st.write(h2h if h2h else "No data found.")

# --- Prepare data summary for AI ---
match_summary = f"""
Match: {home_team} vs {away_team}
Sport: {selected_sport}
Odds:
"""
for bookmaker in selected_event.get('bookmakers', []):
    match_summary += f"\nBookmaker: {bookmaker['title']}"
    for market in bookmaker.get('markets', []):
        if market['key'] == 'h2h':
            for outcome in market['outcomes']:
                match_summary += f"\n  {outcome['name']}: {outcome['price']}"

match_summary += f"\n\n{home_team} Recent Form (last 5):\n" + "\n".join(home_form)
match_summary += f"\n\n{away_team} Recent Form (last 5):\n" + "\n".join(away_form)
match_summary += f"\n\nHead-to-Head (last 5):\n" + "\n".join(h2h)

# --- AI Analysis ---
if st.button("Generate AI Betting Analysis"):
    client = Groq(api_key=GROQ_API_KEY)
    system_prompt = """
You are an expert sports betting analyst. Using the provided odds, match data, recent team form, and head-to-head history, analyze the match, discuss potential value bets, risk factors, and provide actionable betting recommendations. Format your answer as a structured betting analysis.
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
