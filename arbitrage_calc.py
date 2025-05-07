import streamlit as st

def arbitraj_hesapla(butce, oran_a, oran_b, language):
    # Arbitraj oranı hesaplama
    arbitraj_orani = (1 / oran_a) + (1 / oran_b)
    
    # If no arbitrage opportunity
    if arbitraj_orani >= 1:
        if language == 'English':
            st.warning("No arbitrage opportunity. Guaranteed profit cannot be achieved with these odds.")
        else:
            st.warning("Arbitraj fırsatı yok. Bu oranlarla garanti kazanç sağlanamaz.")
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
    st.subheader("Results" if language == 'English' else "Sonuçlar")
    st.write(f"**Bet on Team A**: {bahis_a:.2f} usd" if language == 'English' else f"**Bahis A (Takım A'ya yatırılması gereken tutar)**: {bahis_a:.2f} TL")
    st.write(f"**Bet on Team B**: {bahis_b:.2f} usd" if language == 'English' else f"**Bahis B (Takım B'ye yatırılması gereken tutar)**: {bahis_b:.2f} TL")
    st.write(f"**Total profit**: {min(kar_a, kar_b):.2f} usd" if language == 'English' else f"**Her iki durumda da kazanılacak garanti kar**: {min(kar_a, kar_b):.2f} TL")
    
    total_payout = max(kazanc_a, kazanc_b)
    total_profit = min(kar_a, kar_b)
    roi = (total_profit / butce) * 100

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Payout" if language == 'English' else "Toplam Ödeme", value=f"${total_payout:.2f}")
    with col2:
        st.metric("Total Profit" if language == 'English' else "Toplam Kar", value=f"${total_profit:.2f}")
    with col3:
        st.metric("ROI" if language == 'English' else "ROI", value=f"{roi:.2f}%")

# Streamlit page setup
st.set_page_config(page_title="Arbitrage Calculator", layout="wide")

# Language selection
language = st.radio("Select Language", ('English', 'Türkçe'))

# Title and description
st.title("Arbitrage Calculator" if language == 'English' else "Arbitraj Hesaplama")
st.markdown("""
    This tool helps you calculate arbitrage opportunities between two teams.
    Please enter the odds and budget below.
    """ if language == 'English' else """
    Bu araç, takımlar arasında arbitraj fırsatlarını hesaplamanıza yardımcı olur.
    Lütfen aşağıdaki alanlara bahis oranlarını ve yatırım miktarınızı girin.
""")

# Input fields for odds and budget
col1, col2, col3 = st.columns(3)
with col1:
    oran_a = st.number_input("Enter odds for Team A" if language == 'English' else "Takım A'nın oranını girin", min_value=1.0, step=0.01, value=1.75, format="%.2f")
with col2:
    oran_b = st.number_input("Enter odds for Team B" if language == 'English' else "Takım B'nin oranını girin", min_value=1.0, step=0.01, value=2.5, format="%.2f")
with col3:
    butce = st.number_input("Enter total budget to bet" if language == 'English' else "Yatırılacak toplam bütçeyi girin", min_value=1.0, step=1.0, value=200.0, format="%.2f")

# Calculate button
if st.button("Calculate" if language == 'English' else "Hesapla", key="arbitraj_hesapla"):
    arbitraj_hesapla(butce, oran_a, oran_b, language)













