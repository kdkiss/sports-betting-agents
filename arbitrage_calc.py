import streamlit as st

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
    kar_a = kazanc_a - butce  # Profit if A team wins
    kazanc_b = bahis_b * oran_b
    kar_b = kazanc_b - butce  # Profit if B team wins
    if oran_c and oran_c > 1.0:
        kazanc_c = bahis_c * oran_c
        kar_c = kazanc_c - butce  # Profit if C team wins
        total_profit = min(kar_a, kar_b, kar_c)
        total_payout = max(kazanc_a, kazanc_b, kazanc_c)
    else:
        total_profit = min(kar_a, kar_b)
        total_payout = max(kazanc_a, kazanc_b)

    # Display results
    st.subheader("Results")
    st.write(f"**Bet on Team A**: ${bahis_a:.2f}")
    st.write(f"**Bet on Team B**: ${bahis_b:.2f}")
    if oran_c and oran_c > 1.0:
        st.write(f"**Bet on Team C**: ${bahis_c:.2f}")
    st.write(f"**Total profit**: ${total_profit:.2f}")
    
    roi = (total_profit / butce) * 100 if butce > 0 else 0

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
    This tool helps you calculate arbitrage opportunities between two or three teams.
    Please enter the odds, balance, and risk percentage below. The Team C odds are optional.
""")

# Input fields for odds, balance, and risk percentage
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    oran_a = st.number_input("Enter odds for Team A", min_value=1.0, step=0.01, value=1.75, format="%.2f")
with col2:
    oran_b = st.number_input("Enter odds for Team B", min_value=1.0, step=0.01, value=2.5, format="%.2f")
with col3:
    oran_c = st.number_input("Enter odds for Team C (optional)", min_value=0.0, step=0.01, value=0.0, format="%.2f")
with col4:
    balance = st.number_input("Enter total balance", min_value=1.0, step=1.0, value=1000.0, format="%.2f")
with col5:
    risk_percentage = st.number_input("Risk percentage of balance", min_value=0.0, max_value=100.0, step=0.1, value=20.0, format="%.1f")

# Calculate button
if st.button("Calculate", key="arbitraj_hesapla"):
    arbitraj_hesapla(balance, risk_percentage, oran_a, oran_b, oran_c)
