# AI Agents Hub

This project consolidates several Streamlit-based agents into a single multi-page app.

## Available Agents

- Arbitrage Calculator
- Grammar Checker
- AI Sports Betting Agent
- Bobby Bets Sports Analysis
- Crypto Technical Analysis
- Trading Assistant

## Running the App

Install the dependencies and start Streamlit from the repository root:

```bash
pip install -r requirements.txt
streamlit run main.py
```

The root requirements include packages needed for all agents, including
`langchain` and other dependencies for the Bobby Bets page.
The `sports-betting-agent` folder also contains its own `requirements.txt` for
running that agent standalone, but the packages are duplicated in the root list
for convenience.

Use the sidebar to navigate between pages. Each page simply wraps the original script for its agent so you can access them all in one interface.

## Configuration

Several agents require API keys which should be stored as environment variables. Create a `.env` file in the project root containing:

```
ODDS_API_KEY=your_odds_api_key
GROQ_API_KEY=your_groq_api_key
```

These variables are used by the sports betting and trading assistants. Streamlit will load them automatically when the app runs.
