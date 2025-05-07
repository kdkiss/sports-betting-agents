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

st.set_page_config(page_title="AI Sports Betting Agent with Arbitrage", page_icon="⚽")
st.title("AI Sports Betting Agent with Arbitrage Calculator")

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
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={api_key}®ions=eu&markets={markets}"
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

# --- Arbitrage Calculator ---
def arbitraj_hesapla(butce, oran_a, oran_b, language, team_a, team_b, bookmaker_a, bookmaker_b):
    # Arbitraj oranı hesaplama
    arbitraj_orani = (1 / oran_a) + (1 / oran_b)
    
    # If no arbitrage opportunity
    if arbitraj_orani >= 1:
        if language == 'English':
            st.warning("No arbitrage opportunity. Guaranteed profit cannot be achieved with these odds.")
        else:
            st.warning("Arbitraj fırsatı yok. Bu oranlarla garanti kazanç sağlanamaz.")
        return None

    # A team bet
    bahis_a = (butce / oran_a) / arbitraj_orani
    # B team bet
    bahis_b = (butce / oran_b) / arbitraj_orani
    # Calculate profit in both cases
    kazanc_a = bahis_a * oran_a
    kar_a = kazanc_a - butce  # Profit if A team wins
    kazanc_b = bahis_b * oran_b
    kar_b = kazanc_b - butce  # Profit if B team wins

    # Prepare results
    total_payout = max(kazanc_a, kazanc_b)
    total_profit = min(kar_a, kar_b)
    roi = (total_profit / butce) * 100

    result = {
        'bahis_a': bahis_a,
        'bahis_b': bahis_b,
        'total_payout': total_payout,
        'total_profit': total_profit,
        'roi': roi,
        'team_a': team_a,
        'team_b': team_b,
        'bookmaker_a': bookmaker_a,
        'bookmaker_b': bookmaker_b,
        'oran_a': oran_a,
        'oran_b': oran_b
    }
    return result

# --- Arbitrage Section ---
st.write("### Arbitrage Opportunities")
language = st.radio("Select Language", ('English', 'Türkçe'))

# Input for total budget
butce = st.number_input(
    "Enter total budget to bet" if language == 'English' else "Yatırılacak toplam bütçeyi girin",
    min_value=1.0, step=1.0, value=200.0, format="%.2f"
)

if 'h2h' not in selected_market_keys:
    st.warning("Please select the 'Moneyline (h2h)' market to calculate arbitrage opportunities.")
else:
    # Find best odds for each outcome in h2h market
    h2h_odds = odds_df[odds_df['Market'] == 'h2h']
    if h2h_odds.empty:
        st.warning("No odds available for the Moneyline (h2h) market.")
    else:
        outcomes = h2h_odds.groupby('Outcome')
        best_odds = {}
        for outcome_name, outcome_data in outcomes:
            best_odd = outcome_data['Odds'].max()
            best_bookmaker = outcome_data[outcome_data['Odds'] == best_odd]['Bookmaker'].iloc[0]
            best_odds[outcome_name] = {'odds': best_odd, 'bookmaker': best_bookmaker}

        if len(best_odds) == 2:  # Ensure exactly two outcomes (e.g., Team A and Team B)
            team_a = selected_event['home_team']
            team_b = selected_event['away_team']
            oran_a = best_odds.get(team_a, {}).get('odds')
            oran_b = best_odds.get(team_b, {}).get('odds')
            bookmaker_a = best_odds.get(team_a, {}).get('bookmaker')
            bookmaker_b = best_odds.get(team_b, {}).get('bookmaker')

            if oran_a and oran_b:
                if st.button("Calculate Arbitrage" if language == 'English' else "Arbitraj Hesapla"):
                    result = arbitraj_hesapla(butce, oran_a, oran_b, language, team_a, team_b, bookmaker_a, bookmaker_b)
                    if result:
                        st.subheader("Results" if language == 'English' else "Sonuçlar")
                        st.write(
                            f"**Bet on {team_a} at {bookmaker_a}**: {result['bahis_a']:.2f} {'usd' if language == 'English' else 'TL'}"
                            if language == 'English'
                            else f"**{team_a}'ya {bookmaker_a}'da Bahis**: {result['bahis_a']:.2f} TL"
                        )
                        st.write(
                            f"**Bet on {team_b} at {bookmaker_b}**: {result['bahis_b']:.2f} {'usd' if language == 'English' else 'TL'}"
                            if language == 'English'
                            else f"**{team_b}'ye {bookmaker_b}'da Bahis**: {result['bahis_b']:.2f} TL"
                        )
                        st.write(
                            f"**Total profit**: {result['total_profit']:.2f} {'usd' if language == 'English' else 'TL'}"
                            if language == 'English'
                            else f"**Her iki durumda da kazanılacak garanti kar**: {result['total_profit']:.2f} TL"
                        )

                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric(
                                "Total Payout" if language == 'English' else "Toplam Ödeme",
                                value=f"{'$' if language == 'English' else '₺'}{result['total_payout']:.2f}"
                            )
                        with col2:
                            st.metric(
                                "Total Profit" if language == 'English' else "Toplam Kar",
                                value=f"{'$' if language == 'English' else '₺'}{result['total_profit']:.2f}"
                            )
                        with col3:
                            st.metric(
                                "ROI" if language == 'English' else "ROI",
                                value=f"{result['roi']:.2f}%"
                            )
            else:
                st.warning("Insufficient odds data for both teams to calculate arbitrage.")

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
