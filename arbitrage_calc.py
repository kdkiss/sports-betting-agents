import streamlit as st

def arbitraj_hesapla(balance, risk_percentage, oran_a, oran_b):
    # Calculate budget based on risk percentage
    butce = balance * (risk_percentage / 100)
    
    # Arbitraj oranı hesaplama
    arbitraj_orani = (1 / oran_a) + (1 / oran_b)
    
    # If no arbitrage opportunity
    if arbitraj_orani >= 1:
        st.warning("No arbitrage opportunity. Guaranteed profit cannot be achieved with these odds.")
        return

    # A team bet
    bahis_a = (butce / oran_a) / arbitraj_orani
    # B team bet
    bahis_b = (butce / oran_b) / arbitraj_orani
    # Calculate profit in both cases
    kazanc_a = bahis_a * oran_a
    kar_a = kazanc_a - butce  # Profit if A team wins
    kazanc_b = bahis_b * oran_b
    kar_b = kazanc_b - butce  # Profit if B team wins

    # Display results
    st.subheader("Results")
    st.write(f"**Bet on Team A**: ${bahis_a:.2f}")
    st.write(f"**Bet on Team B**: ${bahis_b:.2f}")
    st.write(f"**Total profit**: ${min(kar_a, kar_b):.2f}")
    
    total_payout = max(kazanc_a, kazanc_b)
    total_profit = min(kar_a, kar_b)
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
    This tool helps you calculate arbitrage opportunities between two teams.
    Please enter the odds, balance, and risk percentage below.
""")

# Input fields for odds, balance, and risk percentage
col1, col2, col3, col4 = st.columns(4)
with col1:
    oran_a = st.number_input("Enter odds for Team A", min_value=1.0, step=0.01, value=1.75, format="%.2f")
with col2:
    oran_b = st.number_input("Enter odds for Team B", min_value=1.0, step=0.01, value=2.5, format="%.2f")
with col3:
    balance = st.number_input("Enter total balance", min_value=1.0, step=1.0, value=1000.0, format="%.2f")
with col4:
    risk_percentage = st.number_input("Risk percentage of balance", min_value=0.0, max_value=100.0, step=0.1, value=20.0, format="%.1f")

# Calculate button
if st.button("Calculate", key="arbitraj_hesapla"):
    arbitraj_hesapla(balance, risk_percentage, oran_a, oran_b)
