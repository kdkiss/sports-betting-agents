import streamlit as st

st.set_page_config(page_title="AI Agents Hub", layout="wide")

st.title("AI Agents Hub")
st.write(
    "Welcome! Use the sidebar or the links below to open each agent page."
)

st.page_link(
    "pages/Arbitrage_Calculator.py",
    label="Arbitrage Calculator",
    icon="📊",
)
st.page_link("pages/Grammar_Checker.py", label="Grammar Checker", icon="✏️")
st.page_link(
    "pages/AI_Sports_Betting_Agent.py",
    label="AI Sports Betting Agent",
    icon="⚽",
)
st.page_link(
    "pages/Bobby_Bets_Sports_Analysis.py",
    label="Bobby Bets Sports Analysis",
    icon="🏀",
)
st.page_link(
    "pages/Crypto_Technical_Analysis.py",
    label="Crypto Technical Analysis",
    icon="💹",
)
st.page_link("pages/Trading_Assistant.py", label="Trading Assistant", icon="📈")

