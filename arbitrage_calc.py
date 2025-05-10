import streamlit as st
import pandas as pd
import uuid
import json
import os

# Directory to store user data
DATA_DIR = "user_data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# File path for user data
def get_user_file(username):
    return os.path.join(DATA_DIR, f"{username}_history.json")

# Load user bet history and balance
def load_user_history(username):
    user_file = get_user_file(username)
    if os.path.exists(user_file):
        with open(user_file, 'r') as f:
            data = json.load(f)
            return pd.DataFrame(data['bet_history']), data['balance']
    return pd.DataFrame(columns=[
        'Bet ID', 'Date', 'Team A Odds', 'Team B Odds', 'Team C Odds', 
        'Bet A', 'Bet B', 'Bet C', 'Total Profit', 'ROI', 'Balance After'
    ]), 100.0

# Save user bet history and balance
def save_user_history(username):
    user_file = get_user_file(username)
    data = {
        'bet_history': st.session_state.bet_history.to_dict('records'),
        'balance': st.session_state.balance
    }
    with open(user_file, 'w') as f:
        json.dump(data, f)

# Arbitrage calculation function
def arbitraj_hesapla(balance, risk_percentage, oran_a, oran_b, oran_c=None, track=False):
    butce = balance * (risk_percentage / 100)
    
    if oran_c and oran_c > 1.0:
        arbitraj_orani = (1 / oran_a) + (1 / oran_b) + (1 / oran_c)
    else:
        arbitraj_orani = (1 / oran_a) + (1 / oran_b)
    
    bahis_a = (butce / oran_a) / arbitraj_orani
    bahis_b = (butce / oran_b) / arbitraj_orani
    bahis_c = (butce / oran_c) / arbitraj_orani if oran_c and oran_c > 1.0 else 0
    
    kazanc_a = bahis_a * oran_a
    kar_a = kazanc_a - butce
    kazanc_b = bahis_b * oran_b
    kar_b = kazanc_b - butce
    if oran_c and oran_c > 1.0:
        kazanc_c = bahis_c * oran_c
        kar_c = kazanc_c - butce
        total_profit = min(kar_a, kar_b, kar_c)
        total_payout = max(kazanc_a, kazanc_b, kazanc_c)
    else:
        total_profit = min(kar_a, kar_b)
        total_payout = max(kazanc_a, kazanc_b)

    roi = (total_profit / butce) * 100 if butce > 0 else 0

    if track:
        st.session_state.balance += total_profit
        bet_id = str(uuid.uuid4())[:8]
        new_bet = pd.DataFrame([{
            'Bet ID': bet_id,
            'Date': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Team A Odds': oran_a,
            'Team B Odds': oran_b,
            'Team C Odds': oran_c if oran_c > 1.0 else None,
            'Bet A': bahis_a,
            'Bet B': bahis_b,
            'Bet C': bahis_c if oran_c > 1.0 else None,
            'Total Profit': total_profit,
            'ROI': roi,
            'Balance After': st.session_state.balance
        }])
        st.session_state.bet_history = pd.concat([st.session_state.bet_history, new_bet], ignore_index=True)
        save_user_history(st.session_state.username)

    st.subheader("Results")
    st.write(f"**Bet on Team A**: ${bahis_a:.2f}")
    st.write(f"**Bet on Team B**: ${bahis_b:.2f}")
    if oran_c and oran_c > 1.0:
        st.write(f"**Bet on Team C**: ${bahis_c:.2f}")
    st.write(f"**Total profit**: ${total_profit:.2f}")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Payout", value=f"${total_payout:.2f}")
    with col2:
        st.metric("Total Profit", value=f"${total_profit:.2f}")
    with col3:
        st.metric("ROI", value=f"{roi:.2f}%")

# Initialize session state
if 'username' not in st.session_state:
    st.session_state.username = None
if 'bet_history' not in st.session_state or 'balance' not in st.session_state:
    st.session_state.bet_history = pd.DataFrame(columns=[
        'Bet ID', 'Date', 'Team A Odds', 'Team B Odds', 'Team C Odds', 
        'Bet A', 'Bet B', 'Bet C', 'Total Profit', 'ROI', 'Balance After'
    ])
    st.session_state.balance = 100.0

st.set_page_config(page_title="Arbitrage Calculator", layout="wide")
st.title("Arbitrage Calculator")
st.markdown("""
    This tool helps you calculate arbitrage opportunities and track bets.
    Enter your username, odds, risk percentage, and view bet history below. Team C odds are optional.
""")

# Username input
st.subheader("User Login")
with st.form(key="username_form"):
    username = st.text_input("Enter Username (e.g., bakingloot)")
    submit_username = st.form_submit_button("Login")
    if submit_username and username:
        st.session_state.username = username
        st.session_state.bet_history, st.session_state.balance = load_user_history(username)
        st.success(f"Logged in as {username}!")

# Main app for logged-in users
if st.session_state.username:
    st.subheader("Set Starting Balance")
    with st.form(key="starting_balance_form"):
        starting_balance = st.number_input("Starting Balance", min_value=0.0, step=1.0, value=st.session_state.balance, format="%.2f")
        submit_balance = st.form_submit_button("Update Starting Balance")
        if submit_balance:
            st.session_state.balance = starting_balance
            st.session_state.bet_history = pd.DataFrame(columns=[
                'Bet ID', 'Date', 'Team A Odds', 'Team B Odds', 'Team C Odds', 
                'Bet A', 'Bet B', 'Bet C', 'Total Profit', 'ROI', 'Balance After'
            ])
            save_user_history(st.session_state.username)
            st.success("Starting balance updated!")

    st.write(f"**Current Balance**: ${st.session_state.balance:.2f}")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        oran_a = st.number_input("Enter odds for Team A", min_value=1.0, step=0.01, value=1.75, format="%.2f", key="logged_odds_a")
    with col2:
        oran_b = st.number_input("Enter odds for Team B", min_value=1.0, step=0.01, value=2.5, format="%.2f", key="logged_odds_b")
    with col3:
        oran_c = st.number_input("Enter odds for Team C (optional)", min_value=0.0, step=0.01, value=0.0, format="%.2f", key="logged_odds_c")
    with col4:
        risk_percentage = st.number_input("Risk percentage of balance", min_value=0.0, max_value=100.0, step=0.1, value=20.0, format="%.1f", key="logged_risk")

    if st.button("Calculate", key="arbitraj_hesapla"):
        arbitraj_hesapla(st.session_state.balance, risk_percentage, oran_a, oran_b, oran_c, track=True)

    st.subheader("Bet History")
    st.dataframe(st.session_state.bet_history, use_container_width=True)

    st.subheader("Edit Bet History")
    bet_id_to_edit = st.selectbox("Select Bet ID to Edit", st.session_state.bet_history['Bet ID'].tolist(), key="edit_bet_id")
    if bet_id_to_edit:
        bet = st.session_state.bet_history[st.session_state.bet_history['Bet ID'] == bet_id_to_edit].iloc[0]
        with st.form(key="edit_bet_form"):
            new_date = st.text_input("Date", value=bet['Date'])
            new_oran_a = st.number_input("Team A Odds", min_value=1.0, step=0.01, value=float(bet['Team A Odds']), format="%.2f")
            new_oran_b = st.number_input("Team B Odds", min_value=1.0, step=0.01, value=float(bet['Team B Odds']), format="%.2f")
            new_oran_c = st.number_input("Team C Odds (optional)", min_value=0.0, step=0.01, value=float(bet['Team C Odds']) if pd.notnull(bet['Team C Odds']) else 0.0, format="%.2f")
            new_bet_a = st.number_input("Bet A", min_value=0.0, step=0.01, value=float(bet['Bet A']), format="%.2f")
            new_bet_b = st.number_input("Bet B", min_value=0.0, step=0.01, value=float(bet['Bet B']), format="%.2f")
            new_bet_c = st.number_input("Bet C", min_value=0.0, step=0.01, value=float(bet['Bet C']) if pd.notnull(bet['Bet C']) else 0.0, format="%.2f")
            new_profit = st.number_input("Total Profit", value=float(bet['Total Profit']), format="%.2f")
            submit_edit = st.form_submit_button("Update Bet")
            if submit_edit:
                old_profit = bet['Total Profit']
                st.session_state.balance = st.session_state.balance - old_profit + new_profit
                st.session_state.bet_history.loc[st.session_state.bet_history['Bet ID'] == bet_id_to_edit, 'Date'] = new_date
                st.session_state.bet_history.loc[st.session_state.bet_history['Bet ID'] == bet_id_to_edit, 'Team A Odds'] = new_oran_a
                st.session_state.bet_history.loc[st.session_state.bet_history['Bet ID'] == bet_id_to_edit, 'Team B Odds'] = new_oran_b
                st.session_state.bet_history.loc[st.session_state.bet_history['Bet ID'] == bet_id_to_edit, 'Team C Odds'] = new_oran_c if new_oran_c > 1.0 else None
                st.session_state.bet_history.loc[st.session_state.bet_history['Bet ID'] == bet_id_to_edit, 'Bet A'] = new_bet_a
                st.session_state.bet_history.loc[st.session_state.bet_history['Bet ID'] == bet_id_to_edit, 'Bet B'] = new_bet_b
                st.session_state.bet_history.loc[st.session_state.bet_history['Bet ID'] == bet_id_to_edit, 'Bet C'] = new_bet_c if new_oran_c > 1.0 else None
                st.session_state.bet_history.loc[st.session_state.bet_history['Bet ID'] == bet_id_to_edit, 'Total Profit'] = new_profit
                st.session_state.bet_history.loc[st.session_state.bet_history['Bet ID'] == bet_id_to_edit, 'Balance After'] = st.session_state.balance
                st.session_state.bet_history.loc[st.session_state.bet_history['Bet ID'] == bet_id_to_edit, 'ROI'] = (new_profit / (new_bet_a + new_bet_b + (new_bet_c if new_oran_c > 1.0 else 0))) * 100 if (new_bet_a + new_bet_b + (new_bet_c if new_oran_c > 1.0 else 0)) > 0 else 0
                save_user_history(st.session_state.username)
                st.success("Bet updated successfully!")

# Simple arbitrage calculator on login page
st.subheader("Quick Arbitrage Calculator (No Login Required)")
st.markdown("Calculate arbitrage opportunities without tracking or logging in.")
col1, col2, col3, col4 = st.columns(4)
with col1:
    quick_oran_a = st.number_input("Odds for Team A", min_value=1.0, step=0.01, value=1.75, format="%.2f", key="quick_odds_a")
with col2:
    quick_oran_b = st.number_input("Odds for Team B", min_value=1.0, step=0.01, value=2.5, format="%.2f", key="quick_odds_b")
with col3:
    quick_oran_c = st.number_input("Odds for Team C (optional)", min_value=0.0, step=0.01, value=0.0, format="%.2f", key="quick_odds_c")
with col4:
    quick_balance = st.number_input("Total Balance", min_value=1.0, step=1.0, value=100.0, format="%.2f", key="quick_balance")
    quick_risk_percentage = st.number_input("Risk Percentage", min_value=0.0, max_value=100.0, step=0.1, value=20.0, format="%.1f", key="quick_risk")

if st.button("Calculate (Quick)", key="quick_arbitraj_hesapla"):
    arbitraj_hesapla(quick_balance, quick_risk_percentage, quick_oran_a, quick_oran_b, quick_oran_c, track=False)
