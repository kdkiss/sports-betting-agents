import streamlit as st
import pandas as pd
import uuid

# Initialize session state for bet history
if 'bet_history' not in st.session_state:
    st.session_state.bet_history = pd.DataFrame(columns=[
        'Bet ID', 'Date', 'Team A Odds', 'Team B Odds', 'Team C Odds', 
        'Bet A', 'Bet B', 'Bet C', 'Total Profit', 'ROI', 'Balance After'
    ])
if 'balance' not in st.session_state:
    st.session_state.balance = 100.0  # Starting balance

def arbitraj_hesapla(balance, risk_percentage, oran_a, oran_b, oran_c=None):
    # Calculate budget based on risk percentage
    butce = balance * (risk_percentage / 100)
    
    # Arbitraj oranı hesaplama
    if oran_c and oran_c > 1.0:
        arbitraj_orani = (1 / oran_a) + (1 / oran_b) + (1 / oran_c)
    else:
        arbitraj_orani = (1 / oran_a) + (1 / oran_b)
    
    # Calculate bets
    bahis_a = (butce / oran_a) / arbitraj_orani
    bahis_b = (butce / oran_b) / arbitraj_orani
    bahis_c = (butce / oran_c) / arbitraj_orani if oran_c and oran_c > 1.0 else 0
    
    # Calculate profit in each case
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

    # Calculate ROI
    roi = (total_profit / butce) * 100 if butce > 0 else 0

    # Update balance
    st.session_state.balance += total_profit

    # Log bet to history
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

    # Display results
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

# Streamlit page setup
st.set_page_config(page_title="Arbitrage Calculator", layout="wide")

# Title and description
st.title("Arbitrage Calculator")
st.markdown("""
    This tool helps you calculate arbitrage opportunities and track bets starting with $100.
    Enter odds, risk percentage, and view bet history below. Team C odds are optional.
""")

# Display current balance
st.write(f"**Current Balance**: ${st.session_state.balance:.2f}")

# Input fields for odds and risk percentage
col1, col2, col3, col4 = st.columns(4)
with col1:
    oran_a = st.number_input("Enter odds for Team A", min_value=1.0, step=0.01, value=1.75, format="%.2f")
with col2:
    oran_b = st.number_input("Enter odds for Team B", min_value=1.0, step=0.01, value=2.5, format="%.2f")
with col3:
    oran_c = st.number_input("Enter odds for Team C (optional)", min_value=0.0, step=0.01, value=0.0, format="%.2f")
with col4:
    risk_percentage = st.number_input("Risk percentage of balance", min_value=0.0, max_value=100.0, step=0.1, value=20.0, format="%.1f")

# Calculate button
if st.button("Calculate", key="arbitraj_hesapla"):
    arbitraj_hesapla(st.session_state.balance, risk_percentage, oran_a, oran_b, oran_c)

# Bet history display
st.subheader("Bet History")
st.dataframe(st.session_state.bet_history, use_container_width=True)

# Edit bet history
st.subheader("Edit Bet History")
bet_id_to_edit = st.selectbox("Select Bet ID to Edit", st.session_state.bet_history['Bet ID'].tolist(), key="edit_bet_id")
if bet_id_to_edit:
    bet = st.session_state.bet_history[st.session_state.bet_history['Bet ID'] == bet_id_to_edit].iloc[0]
    with st.form(key="edit_bet_form"):
        new_profit = st.number_input("New Total Profit", value=float(bet['Total Profit']), format="%.2f")
        submit_edit = st.form_submit_button("Update Bet")
        if submit_edit:
            # Update balance by reversing old profit and applying new profit
            old_profit = bet['Total Profit']
            st.session_state.balance = st.session_state.balance - old_profit + new_profit
            # Update bet history
            st.session_state.bet_history.loc[st.session_state.bet_history['Bet ID'] == bet_id_to_edit, 'Total Profit'] = new_profit
            st.session_state.bet_history.loc[st.session_state.bet_history['Bet ID'] == bet_id_to_edit, 'Balance After'] = st.session_state.balance
            st.session_state.bet_history.loc[st.session_state.bet_history['Bet ID'] == bet_id_to_edit, 'ROI'] = (new_profit / (bet['Bet A'] + bet['Bet B'] + (bet['Bet C'] if pd.notnull(bet['Bet C']) else 0))) * 100
            st.success("Bet updated successfully!")
