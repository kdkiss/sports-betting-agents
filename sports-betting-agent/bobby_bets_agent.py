import asyncio
import httpx
from bs4 import BeautifulSoup
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from typing import Dict, Any, List
import re
from datetime import datetime, timedelta
from langchain.callbacks.base import BaseCallbackHandler
import sqlite3
import json
import logging
from dotenv import load_dotenv
import os
import groq

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Groq API key
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in .env file")

# Initialize SQLite database
def init_sqlite_db():
    conn = sqlite3.connect("user_memory.db", timeout=10)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            memory TEXT,
            metadata TEXT
        )
    """)
    conn.commit()
    conn.close()

# Run init at startup
init_sqlite_db()

# NBA team dictionaries (same as original)
TEAM_CODES = {
    "hawks": "atl", "atlanta": "atl",
    "celtics": "bos", "boston": "bos",
    "nets": "bkn", "brooklyn": "bkn",
    "hornets": "cha", "charlotte": "cha",
    "bulls": "chi", "chicago": "chi",
    "cavaliers": "cle", "cleveland": "cle",
    "mavericks": "dal", "dallas": "dal",
    "nuggets": "den", "denver": "den",
    "pistons": "det", "detroit": "det",
    "warriors": "gsw", "golden state": "gsw",
    "rockets": "hou", "houston": "hou",
    "pacers": "ind", "indiana": "ind",
    "clippers": "lac", "la clippers": "lac",
    "lakers": "lal", "los angeles lakers": "lal", "la lakers": "lal",
    "grizzlies": "mem", "memphis": "mem",
    "heat": "mia", "miami": "mia",
    "bucks": "mil", "milwaukee": "mil",
    "timberwolves": "min", "minnesota": "min",
    "pelicans": "no", "new orleans": "no",
    "knicks": "ny", "new york": "ny",
    "thunder": "okc", "oklahoma city": "okc",
    "magic": "orl", "orlando": "orl",
    "76ers": "phi", "philadelphia": "phi", "sixers": "phi",
    "suns": "phx", "phoenix": "phx",
    "trail blazers": "por", "portland": "por",
    "kings": "sac", "sacramento": "sac",
    "spurs": "sa", "san antonio": "sa",
    "raptors": "tor", "toronto": "tor",
    "jazz": "utah", "utah": "utah",
    "wizards": "wsh", "washington": "wsh"
}

BBALL_REF_CODES = {
    "hawks": "ATL", "atlanta": "ATL",
    "celtics": "BOS", "boston": "BOS",
    "nets": "BKN", "brooklyn": "BKN",
    "hornets": "CHA", "charlotte": "CHA",
    "bulls": "CHI", "chicago": "CHI",
    "cavaliers": "CLE", "cleveland": "CLE",
    "mavericks": "DAL", "dallas": "DAL",
    "nuggets": "DEN", "denver": "DEN",
    "pistons": "DET", "detroit": "DET",
    "warriors": "GSW", "golden state": "GSW",
    "rockets": "HOU", "houston": "HOU",
    "pacers": "IND", "indiana": "IND",
    "clippers": "LAC", "la clippers": "LAC",
    "lakers": "LAL", "los angeles lakers": "LAL", "la lakers": "LAL",
    "grizzlies": "MEM", "memphis": "MEM",
    "heat": "MIA", "miami": "MIA",
    "bucks": "MIL", "milwaukee": "MIL",
    "timberwolves": "MIN", "minnesota": "MIN",
    "pelicans": "NOP", "new orleans": "NOP",
    "knicks": "NYK", "new york": "NYK",
    "thunder": "OKC", "oklahoma city": "OKC",
    "magic": "ORL", "orlando": "ORL",
    "76ers": "PHI", "philadelphia": "PHI", "sixers": "PHI",
    "suns": "PHX", "phoenix": "PHX",
    "trail blazers": "POR", "portland": "POR",
    "kings": "SAC", "sacramento": "SAC",
    "spurs": "SAS", "san antonio": "SAS",
    "raptors": "TOR", "toronto": "TOR",
    "jazz": "UTA", "utah": "UTA",
    "wizards": "WAS", "washington": "WAS"
}

SCORES24_NBA_NAMES = {
    "hawks": "atlanta-hawks", "atlanta": "atlanta-hawks",
    "celtics": "boston-celtics", "boston": "boston-celtics",
    "nets": "brooklyn-nets", "brooklyn": "brooklyn-nets",
    "hornets": "charlotte-hornets", "charlotte": "charlotte-hornets",
    "bulls": "chicago-bulls", "chicago": "chicago-bulls",
    "cavaliers": "cleveland-cavaliers", "cleveland": "cleveland-cavaliers",
    "mavericks": "dallas-mavericks", "dallas": "dallas-mavericks",
    "nuggets": "denver-nuggets", "denver": "denver-nuggets",
    "pistons": "detroit-pistons", "detroit": "detroit-pistons",
    "warriors": "golden-state-warriors", "golden state": "golden-state-warriors",
    "rockets": "houston-rockets", "houston": "houston-rockets",
    "pacers": "indiana-pacers", "indiana": "indiana-pacers",
    "clippers": "los-angeles-clippers", "la clippers": "los-angeles-clippers",
    "lakers": "los-angeles-lakers", "los angeles lakers": "los-angeles-lakers", "la lakers": "los-angeles-lakers",
    "grizzlies": "memphis-grizzlies", "memphis": "memphis-grizzlies",
    "heat": "miami-heat", "miami": "miami-heat",
    "bucks": "milwaukee-bucks", "milwaukee": "milwaukee-bucks",
    "timberwolves": "minnesota-timberwolves", "minnesota": "minnesota-timberwolves",
    "pelicans": "new-orleans-pelicans", "new orleans": "new-orleans-pelicans",
    "knicks": "new-york-knicks", "new york": "new-york-knicks",
    "thunder": "oklahoma-city-thunder", "oklahoma city": "oklahoma-city-thunder",
    "magic": "orlando-magic", "orlando": "orlando-magic",
    "76ers": "philadelphia-76ers", "philadelphia": "philadelphia-76ers", "sixers": "philadelphia-76ers",
    "suns": "phoenix-suns", "phoenix": "phoenix-suns",
    "trail blazers": "portland-trail-blazers", "portland": "portland-trail-blazers",
    "kings": "sacramento-kings", "sacramento": "sacramento-kings",
    "spurs": "san-antonio-spurs", "san antonio": "san-antonio-spurs",
    "raptors": "toronto-raptors", "toronto": "toronto-raptors",
    "jazz": "utah-jazz", "utah": "utah-jazz",
    "wizards": "washington-wizards", "washington": "washington-wizards"
}

# Football team dictionaries (same as original)
SCORES24_FOOTBALL_NAMES = {
    # Germany
    "bayern": "bayern-munich", "bayern munich": "bayern-munich", "bayern münchen": "bayern-munich",
    "dortmund": "borussia-dortmund", "borussia dortmund": "borussia-dortmund",
    "leverkusen": "bayer-leverkusen", "bayer leverkusen": "bayer-leverkusen",
    "leipzig": "rb-leipzig", "rb leipzig": "rb-leipzig",
    "frankfurt": "eintracht-frankfurt", "eintracht frankfurt": "eintracht-frankfurt",
    "stuttgart": "vfb-stuttgart", "vfb stuttgart": "vfb-stuttgart",
    "mainz": "mainz-05", "mainz 05": "mainz-05",
    "augsburg": "augsburg",
    "bremen": "werder-bremen", "werder bremen": "werder-bremen",
    "freiburg": "freiburg",
    "monchengladbach": "borussia-monchengladbach", "borussia mönchengladbach": "borussia-monchengladbach",
    "wolfsburg": "wolfsburg",
    "union berlin": "union-berlin", "berlin": "hertha-berlin", "hertha": "hertha-berlin",
    "hoffenheim": "hoffenheim",
    "dusseldorf": "fortuna-dusseldorf", "fortuna düsseldorf": "fortuna-dusseldorf",
    "hamburg": "hamburger-sv", "hamburger sv": "hamburger-sv",
    "koln": "koln", "cologne": "koln", "1. fc köln": "koln",
    "schalke": "schalke-04", "schalke 04": "schalke-04",
    # England
    "man united": "manchester-united", "man utd": "manchester-united", "manchester united": "manchester-united",
    "liverpool": "liverpool",
    "arsenal": "arsenal",
    "chelsea": "chelsea",
    "man city": "manchester-city", "manchester city": "manchester-city",
    "tottenham": "tottenham-hotspur", "spurs": "tottenham-hotspur",
    "newcastle": "newcastle-united", "newcastle united": "newcastle-united",
    "west ham": "west-ham-united", "west ham united": "west-ham-united",
    "everton": "everton",
    "aston villa": "aston-villa", "villa": "aston-villa",
    "leicester": "leicester-city", "leicester city": "leicester-city",
    "crystal palace": "crystal-palace",
    "wolves": "wolverhampton-wanderers", "wolverhampton": "wolverhampton-wanderers",
    "brighton": "brighton-hove-albion", "brighton & hove": "brighton-hove-albion",
    "fulham": "fulham",
    "nottingham": "nottingham-forest", "nottingham forest": "nottingham-forest",
    "bournemouth": "bournemouth",
    "brentford": "brentford",
    "athletic club": "athletic-club", "athletic": "athletic-club",
    # Spain
    "real madrid": "real-madrid", "madrid": "real-madrid",
    "barcelona": "barcelona", "barca": "barcelona",
    "atletico": "atletico-madrid", "atletico madrid": "atletico-madrid",
    "sevilla": "sevilla",
    "valencia": "valencia",
    "villarreal": "villarreal",
    "betis": "real-betis", "real betis": "real-betis",
    "athletic bilbao": "athletic-bilbao", "athletic": "athletic-bilbao",
    "real sociedad": "real-sociedad",
    "osasuna": "osasuna",
    "celta": "celta-vigo", "celta vigo": "celta-vigo",
    "granada": "granada",
    "alaves": "alaves",
    "getafe": "getafe",
    "mallorca": "mallorca",
    "cadiz": "cadiz",
    "rayo": "rayo-vallecano", "rayo vallecano": "rayo-vallecano",
    "almeria": "almeria",
    "girona": "girona",
    "las palmas": "las-palmas",
    # Italy
    "juventus": "juventus",
    "inter": "inter-milan", "internazionale": "inter-milan", "inter milan": "inter-milan",
    "ac milan": "ac-milan", "milan": "ac-milan",
    "napoli": "napoli",
    "roma": "roma",
    "lazio": "lazio",
    "atalanta": "atalanta",
    "fiorentina": "fiorentina",
    "torino": "torino",
    "udinese": "udinese",
    "sassuolo": "sassuolo",
    "bologna": "bologna",
    "genoa": "genoa",
    "cagliari": "cagliari",
    "empoli": "empoli",
    "verona": "hellas-verona", "hellas verona": "hellas-verona",
    "lecce": "lecce",
    "monza": "monza",
    "parma": "parma",
    "sampdoria": "sampdoria",
    "salernitana": "salernitana",
    "como": "como",
}

FOOTBALL_CODES = {
    # Germany (Bundesliga)
    "bayern": "MUN", "bayern munich": "MUN", "bayern münchen": "MUN",
    "dortmund": "DOR", "borussia dortmund": "DOR",
    "leverkusen": "LEV", "bayer leverkusen": "LEV",
    "leipzig": "RBL", "rb leipzig": "RBL",
    "frankfurt": "SGE", "eintracht frankfurt": "SGE",
    "stuttgart": "VFB", "vfb stuttgart": "VFB",
    "mainz": "M05", "mainz 05": "M05",
    "augsburg": "FCA",
    "bremen": "SVW", "werder bremen": "SVW",
    "freiburg": "SCF",
    "monchengladbach": "BMG", "borussia mönchengladbach": "BMG",
    "wolfsburg": "WOB",
    "union berlin": "FCU", "berlin": "BSC", "hertha": "BSC", "hertha berlin": "BSC",
    "hoffenheim": "TSG",
    "dusseldorf": "F95", "fortuna düsseldorf": "F95",
    "hamburg": "HSV", "hamburger sv": "HSV",
    "koln": "KOE", "cologne": "KOE", "1. fc köln": "KOE",
    "schalke": "S04", "schalke 04": "S04",
    # England (Premier League)
    "man united": "MUN", "man utd": "MUN", "manchester united": "MUN",
    "liverpool": "LIV",
    "arsenal": "ARS",
    "chelsea": "CHE",
    "man city": "MCI", "manchester city": "MCI",
    "tottenham": "TOT", "spurs": "TOT",
    "newcastle": "NEW", "newcastle united": "NEW",
    "west ham": "WHU", "west ham united": "WHU",
    "everton": "EVE",
    "aston villa": "AVL", "villa": "AVL",
    "leicester": "LEI", "leicester city": "LEI",
    "crystal palace": "CRY",
    "wolves": "WOL", "wolverhampton": "WOL",
    "brighton": "BHA", "brighton & hove": "BHA",
    "fulham": "FUL",
    "nottingham": "NFO", "nottingham forest": "NFO",
    "bournemouth": "BOU",
    "brentford": "BRE",
    "southampton": "SOU",
    "leeds": "LEE", "leeds united": "LEE",
    "sheffield united": "SHU",
    "burnley": "BUR",
    "ipswich": "IPS", "ipswich town": "IPS",
    "athletic club": "ath", "athletic": "ath",
    # Spain (LaLiga)
    "real madrid": "RMA", "madrid": "RMA",
    "barcelona": "BAR", "barca": "BAR",
    "atletico": "ATM", "atletico madrid": "ATM",
    "sevilla": "SEV",
    "valencia": "VAL",
    "villarreal": "VIL",
    "betis": "BET", "real betis": "BET",
    "athletic bilbao": "ATH", "athletic": "ATH",
    "real sociedad": "RSO",
    "osasuna": "OSA",
    "celta": "CEL", "celta vigo": "CEL",
    "granada": "GRA",
    "alaves": "ALA",
    "getafe": "GET",
    "mallorca": "MLL",
    "cadiz": "CAD",
    "rayo": "RAY", "rayo vallecano": "RAY",
    "almeria": "ALM",
    "girona": "GIR",
    "las palmas": "LPA",
    # Italy (Serie A)
    "juventus": "JUV",
    "inter": "INT", "internazionale": "INT", "inter milan": "INT",
    "ac milan": "MIL", "milan": "MIL",
    "napoli": "NAP",
    "roma": "ROM",
    "lazio": "LAZ",
    "atalanta": "ATA",
    "fiorentina": "FIO",
    "torino": "TOR",
    "udinese": "UDI",
    "sassuolo": "SAS",
    "bologna": "BOL",
    "genoa": "GEN",
    "cagliari": "CAG",
    "empoli": "EMP",
    "verona": "VER", "hellas verona": "VER",
    "lecce": "LEC",
    "monza": "MON",
    "parma": "PAR",
    "sampdoria": "SAM",
    "salernitana": "SAL",
    "como": "COM",
}

FOOTBALL_REF_CODES = {
    # Germany (Bundesliga)
    "bayern": "FCB", "bayern munich": "FCB", "bayern münchen": "FCB",
    "dortmund": "BVB", "borussia dortmund": "BVB",
    "leverkusen": "B04", "bayer leverkusen": "B04",
    "leipzig": "RBL", "rb leipzig": "RBL",
    "frankfurt": "SGE", "eintracht frankfurt": "SGE",
    "stuttgart": "VFB", "vfb stuttgart": "VFB",
    "mainz": "M05", "mainz 05": "M05",
    "augsburg": "FCA",
    "bremen": "SVW", "werder bremen": "SVW",
    "freiburg": "SCF",
    "monchengladbach": "BMG", "borussia mönchengladbach": "BMG",
    "wolfsburg": "WOB",
    "union berlin": "FCU", "hertha": "BSC", "hertha berlin": "BSC",
    "hoffenheim": "TSG",
    "dusseldorf": "F95", "fortuna düsseldorf": "F95",
    "hamburg": "HSV", "hamburger sv": "HSV",
    "koln": "KOE", "cologne": "KOE", "1. fc köln": "KOE",
    "schalke": "S04", "schalke 04": "S04",
    # England (Premier League)
    "man united": "MUN", "man utd": "MUN", "manchester united": "MUN",
    "liverpool": "LIV",
    "arsenal": "ARS",
    "chelsea": "CHE",
    "man city": "MCI", "manchester city": "MCI",
    "tottenham": "TOT", "spurs": "TOT",
    "newcastle": "NEW", "newcastle united": "NEW",
    "west ham": "WHU", "west ham united": "WHU",
    "everton": "EVE",
    "aston villa": "AVL", "villa": "AVL",
    "leicester": "LEI", "leicester city": "LEI",
    "crystal palace": "CRY",
    "wolves": "WOL", "wolverhampton": "WOL",
    "brighton": "BHA", "brighton & hove": "BHA",
    "fulham": "FUL",
    "nottingham": "NFO", "nottingham forest": "NFO",
    "bournemouth": "BOU",
    "brentford": "BRE",
    "southampton": "SOU",
    "leeds": "LEE", "leeds united": "LEE",
    "sheffield united": "SHU",
    "burnley": "BUR",
    "ipswich": "IPS", "ipswich town": "IPS",
    "athletic club": "ATH", "athletic": "ATH",
    # Spain (LaLiga)
    "real madrid": "RMA", "madrid": "RMA",
    "barcelona": "BAR", "barca": "BAR",
    "atletico": "ATM", "atletico madrid": "ATM",
    "sevilla": "SEV",
    "valencia": "VAL",
    "villarreal": "VIL",
    "betis": "BET", "real betis": "BET",
    "athletic bilbao": "ATH", "athletic": "ATH",
    "real sociedad": "RSO",
    "osasuna": "OSA",
    "celta": "CEL", "celta vigo": "CEL",
    "granada": "GRA",
    "alaves": "ALA",
    "getafe": "GET",
    "mallorca": "MLL",
    "cadiz": "CAD",
    "rayo": "RAY", "rayo vallecano": "RAY",
    "almeria": "ALM",
    "girona": "GIR",
    "las palmas": "LPA",
    # Italy (Serie A)
    "juventus": "JUV",
    "inter": "INT", "internazionale": "INT", "inter milan": "INT",
    "ac milan": "MIL", "milan": "MIL",
    "napoli": "NAP",
    "roma": "ROM",
    "lazio": "LAZ",
    "atalanta": "ATA",
    "fiorentina": "FIO",
    "torino": "TOR",
    "udinese": "UDI",
    "sassuolo": "SAS",
    "bologna": "BOL",
    "genoa": "GEN",
    "cagliari": "CAG",
    "empoli": "EMP",
    "verona": "VER", "hellas verona": "VER",
    "lecce": "LEC",
    "monza": "MON",
    "parma": "PAR",
    "sampdoria": "SAM",
    "salernitana": "SAL",
    "como": "COM",
}

# HTTP client for fetching web pages
async def fetch_page(url: str) -> str:
    """Fetch a webpage using httpx and return its HTML content."""
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
            response = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
            return response.text
    except Exception as e:
        logger.error(f"Error fetching {url}: {str(e)}")
        return f"Error fetching {url}: {str(e)}"

# Parse HTML content
def parse_html(html: str, keywords: List[str] = None) -> str:
    """Parse HTML content with BeautifulSoup and extract relevant data."""
    try:
        soup = BeautifulSoup(html, "html.parser")
        # Remove scripts and styles for cleaner text
        for script in soup(["script", "style"]):
            script.decompose()
        text = soup.get_text(separator="\n", strip=True)
        if keywords:
            lines = text.split("\n")
            relevant_lines = [line for line in lines if any(keyword.lower() in line.lower() for keyword in keywords)]
            return "\n".join(relevant_lines) if relevant_lines else "No relevant data found."
        return text
    except Exception as e:
        logger.error(f"Error parsing HTML: {str(e)}")
        return f"Error parsing HTML: {str(e)}"

# Updated fetch_team_schedule tool
@tool
async def fetch_team_schedule(teams_and_params: str, sport: str = "nba") -> str:
    """Fetch the game schedule for specified teams and date using httpx."""
    try:
        parts = teams_and_params.lower().split()
        date = None
        teams = []
        for part in parts:
            if re.match(r"\d{4}-\d{2}-\d{2}", part):
                date = part
            elif sport == "nba" and part in TEAM_CODES:
                teams.append(part)
            elif sport == "football" and part in FOOTBALL_CODES:
                teams.append(part)
        
        if len(teams) < 1:
            return f"Error: At least one {sport} team must be specified."
        
        team_dict = TEAM_CODES if sport == "nba" else FOOTBALL_CODES
        team_code = team_dict[teams[0]]
        if sport == "nba":
            url = f"https://www.espn.com/nba/team/schedule/_/name/{team_code}"
            fallback_url = f"https://www.nba.com/schedule?team={team_code}"
        else:
            url = f"https://www.espn.com/soccer/team/fixtures/_/id/{team_code}"
            fallback_url = f"https://www.flashscore.com/team/{team_code}/2025"
        logger.info(f"Fetching {sport} schedule for {teams[0]} from {url}")
        
        # Try primary URL
        html = await fetch_page(url)
        if "Error fetching" in html:
            logger.warning(f"Primary URL failed for {url}. Trying fallback {fallback_url}")
            html = await fetch_page(fallback_url)
        
        # Parse schedule
        schedule_data = parse_html(html, keywords=["date", "vs", "at"] if sport == "nba" else ["date", "vs", "at", "fixture"])
        games = []
        lines = schedule_data.split("\n")
        for line in lines:
            if date and date in line:
                games.append(line)
            elif not date and any(team in line.lower() for team in teams):
                games.append(line)
        
        if not games:
            if date:
                try:
                    input_date = datetime.strptime(date, "%Y-%m-%d")
                    closest_date = None
                    closest_diff = timedelta(days=365)
                    for line in lines:
                        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", line)
                        if date_match:
                            game_date = datetime.strptime(date_match.group(1), "%Y-%m-%d")
                            diff = abs(game_date - input_date)
                            if diff < closest_diff:
                                closest_diff = diff
                                closest_date = game_date
                                games = [line]
                    if closest_date:
                        return f"No {sport} game found on {date}. Closest game found on {closest_date.strftime('%Y-%m-%d')}:\n{''.join(games)}\nADJUSTED_DATE: {closest_date.strftime('%Y-%m-%d')}\nURL: {url}"
                except ValueError:
                    pass
            return f"No {sport} games found for {teams[0]}.\nURL: {url}"
        
        return f"{sport.capitalize()} schedule for {teams[0]}:\n{''.join(games)}\nURL: {url}"
    except Exception as e:
        logger.error(f"Error fetching {sport} schedule: {str(e)}")
        return f"Error fetching {sport} schedule: {str(e)}"

@tool
def extract_team_names(text: str, sport: str = "nba") -> Dict[str, str]:
    """Extract team names from the provided text for the specified sport."""
    text = text.lower()
    team1 = None
    team2 = None
    team_dict = TEAM_CODES if sport == "nba" else FOOTBALL_CODES
    for team in team_dict.keys():
        if team in text:
            if not team1:
                team1 = team
            elif not team2 and team != team1:
                team2 = team
        if team1 and team2:
            break
    return {"team1": team1, "team2": team2, "sport": sport} if team1 else {"error": f"No valid {sport} teams found"}

@tool
async def fetch_team_stats(team_name: str, sport: str = "nba") -> str:
    """Fetch team statistics and injury reports using httpx."""
    try:
        team_dict = BBALL_REF_CODES if sport == "nba" else FOOTBALL_REF_CODES
        if team_name not in team_dict:
            return f"Error: Invalid {sport} team name {team_name}"
        
        team_code = team_dict[team_name]
        if sport == "nba":
            url = f"https://www.basketball-reference.com/teams/{team_code}/2025.html"
            fallback_url = f"https://www.nba.com/stats/team/{team_code}"
        else:
            url = f"https://www.soccerway.com/teams/{team_code}/2025"
            fallback_url = f"https://www.flashscore.com/team/{team_code}/2025"
        logger.info(f"Fetching {sport} stats for {team_name} from {url}")
        
        html = await fetch_page(url)
        if "Error fetching" in html:
            logger.warning(f"Primary URL failed for {url}. Trying fallback {fallback_url}")
            html = await fetch_page(fallback_url)
        
        keywords = ["points", "rebounds", "assists", "fg%", "injury"] if sport == "nba" else ["goals", "assists", "possession", "shots", "injury"]
        stats_data = parse_html(html, keywords=keywords)
        
        return f"{sport.capitalize()} stats for {team_name}:\n{stats_data}\nURL: {url}"
    except Exception as e:
        logger.error(f"Error fetching {sport} stats for {team_name}: {str(e)}")
        return f"Error fetching {sport} stats for {team_name}: {str(e)}"

@tool
async def fetch_betting_trends(team1: str, team2: str, date: str, sport: str = "nba") -> str:
    """Fetch betting trends for a specific matchup using httpx."""
    try:
        team_dict = SCORES24_NBA_NAMES if sport == "nba" else SCORES24_FOOTBALL_NAMES
        if team1 not in team_dict or team2 not in team_dict:
            return f"Error: Invalid {sport} team names {team1} or {team2}"
        
        team1_code = team_dict[team1]
        team2_code = team_dict[team2]
        sport_path = "basketball" if sport == "nba" else "football"
        url = f"https://scores24.live/en/{sport_path}/h2h/{team1_code}-vs-{team2_code}"
        fallback_url = f"https://www.oddsportal.com/{sport_path}/{team1_code}-vs-{team2_code}"
        logger.info(f"Fetching {sport} betting trends for {team1} vs {team2} from {url}")
        
        html = await fetch_page(url)
        if "Error fetching" in html:
            logger.warning(f"Primary URL failed for {url}. Trying fallback {fallback_url}")
            html = await fetch_page(fallback_url)
        
        trends_data = parse_html(html, keywords=["odds", "spread", "over/under", "moneyline"])
        
        return f"{sport.capitalize()} betting trends for {team1} vs {team2} on {date}:\n{trends_data}\nSource: {url}"
    except Exception as e:
        logger.error(f"Error fetching {sport} betting trends: {str(e)}")
        return f"Error fetching {sport} betting trends: {str(e)}"

@tool
def analyze_matchup_data(team1_stats: str, team2_stats: str, betting_trends: str, sport: str = "nba") -> str:
    """Analyze matchup data to provide betting insights."""
    try:
        analysis = f"""
# {sport.capitalize()} Matchup Analysis

## Team 1 Stats
{team1_stats}

## Team 2 Stats
{team2_stats}

## Betting Trends
{betting_trends}

## Analysis
- **Team Performance**: Comparing offensive and defensive metrics.
- **Injuries**: Noting any key player absences.
- **Trends**: Evaluating historical betting patterns.

**Predicted Winner**: To be determined by LLM based on data.
**Confidence Level**: To be determined by LLM.
"""
        return analysis
    except Exception as e:
        return f"Error analyzing {sport} matchup data: {str(e)}"

@tool
def manage_memory(action: str, user_id: str = None, memory: str = None, metadata: dict = None) -> str:
    """Manage user memories using SQLite."""
    try:
        conn = sqlite3.connect("user_memory.db", timeout=10)
        cursor = conn.cursor()
        if action == "add" and user_id and memory:
            cursor.execute("INSERT INTO memories (user_id, memory, metadata) VALUES (?, ?, ?)",
                         (user_id, memory, json.dumps(metadata) if metadata else "{}"))
            conn.commit()
            return f"Memory added for user {user_id}"
        elif action == "search" and user_id:
            cursor.execute("SELECT memory, metadata FROM memories WHERE user_id = ?", (user_id,))
            memories = [{"memory": row[0], "metadata": json.loads(row[1])} for row in cursor.fetchall()]
            return json.dumps(memories)
        elif action == "count" and user_id:
            cursor.execute("SELECT COUNT(*) FROM memories WHERE user_id = ?", (user_id,))
            count = cursor.fetchone()[0]
            return f"Total memories for user {user_id}: {count}"
        elif action == "clear" and user_id:
            cursor.execute("DELETE FROM memories WHERE user_id = ?", (user_id,))
            conn.commit()
            return f"Memories cleared for user {user_id}"
        return "Invalid memory action"
    except Exception as e:
        logger.error(f"Error managing memory: {str(e)}")
        return f"Error managing memory: {str(e)}"
    finally:
        conn.close()

# System prompt for the agent (same as original)
system_prompt = """You are Bobby Bets, an expert sports analyst and seasoned bettor with decades of experience in both NBA basketball and European football (soccer). You provide data-driven insights and betting recommendations for NBA and football matches in an authentic, conversational style that sounds like a real sports bettor.

When analyzing matchups, follow these steps:
1. First, check the team schedule to verify if the game exists on the specified date.
2. If a specific date is mentioned but no game exists, automatically use the closest game date.
3. Extract the team names from the user's query and determine the sport (NBA or football).
4. Fetch general team statistics for both teams (including injury reports).
5. If a specific game date is mentioned, fetch betting trends for that matchup.
6. Analyze all the data to provide insights and betting recommendations.

IMPORTANT: When the fetch_team_schedule function returns an "ADJUSTED_DATE" tag, you MUST use this adjusted date for all subsequent tool calls (like fetch_betting_trends) instead of the original date. This ensures you're analyzing the correct game when the user's requested date doesn't have a game scheduled.

When analyzing the data:
- For **NBA**:
  - Look at offensive/defensive ratings, points per game, rebounds, assists, FG%.
  - Compare team records, rankings, and recent form (last 5-10 games).
  - Factor in injuries, home court advantage, and schedule difficulty.
  - Analyze betting trends for moneyline, spread, over/under.
- For **Football**:
  - Look at goals scored/conceded, possession, shots on target, expected goals (xG).
  - Compare league standings, recent form, and head-to-head records.
  - Factor in injuries, home/away performance, and tactical setups.
  - Analyze betting trends for 1X2, over/under goals, both teams to score (BTTS).
- Reference the user's past betting preferences and interests from memory when relevant.

RESPONSE STYLE:
Write your responses like a real sports bettor would talk - use authentic language, slang, and a conversational tone. Include:
1. A clear prediction with a winner (or draw for football).
2. Your confidence level in the prediction (very high, high, moderate, slight edge, or coin flip).
3. The key factors that influenced your prediction.
4. Notable insights you discovered during your research.
5. Specific betting recommendations:
   - For NBA: moneyline, spread, over/under.
   - For football: 1X2, over/under goals, BTTS, Asian handicap.
6. Citations to your information sources.

Don't use a rigid template - vary your language and structure to sound authentic. Use phrases like "I'm taking...", "I'm leaning...", "The smart money is on...", etc. Occasionally mention your personal betting philosophy or approach.

SOURCES AND EVIDENCE:
Always back up your predictions with specific data points and evidence. For example:
- NBA: "I'm taking the Celtics because they're 8-2 in their last 10 home games against teams with winning records."
- Football: "Bayern's averaging 2.5 goals per game at home, while Dortmund's defense has conceded 1.8 goals per game on the road."

Be sure to cite your sources clearly. Mention where you got your information from, such as:
- NBA: Basketball Reference, ESPN, scores24.live.
- Football: Soccerway, ESPN, scores24.live.
- Injury reports, betting trends, head-to-head history, rest days/schedule.

Your insights should be data-driven but also consider context like injuries, schedule difficulty, and team strengths/weaknesses.

When communicating with the user about an adjusted date:
1. Be transparent that you've adjusted to the closest game date.
2. Explain why (e.g., "There is no game scheduled on March 18, so I'm analyzing the closest game on March 14 instead").
3. Provide your analysis based on the adjusted date.

MEMORY SYSTEM:
You have access to a memory system that stores information about users and their preferences. Use this to:
1. Remember which teams and sports a user has shown interest in previously.
2. Recall a user's betting preferences (e.g., NBA spread bets, football BTTS bets).
3. Reference past analyses and predictions you've made for the user.
4. Personalize your responses based on the user's history.

When a user asks about teams they've previously inquired about, acknowledge this and reference your previous analysis if relevant.
"""

# Create a proper ChatPromptTemplate from the system prompt
prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", "{input}"),
    ("human", "{agent_scratchpad}")
])

# Create a custom callback handler to handle date adjustments
class DateAdjustmentHandler(BaseCallbackHandler):
    """Callback handler that adjusts dates in tool inputs based on ADJUSTED_DATE tags."""
    
    def __init__(self):
        """Initialize the handler."""
        super().__init__()
        self.adjusted_date = None
        self.original_date = None
    
    def on_agent_action(self, action, **kwargs) -> None:
        """Process agent actions to adjust dates if needed."""
        if self.adjusted_date and self.original_date and self.adjusted_date != self.original_date:
            tool_input = action.tool_input
            if isinstance(tool_input, dict) and "date" in tool_input:
                if tool_input["date"] == self.original_date:
                    tool_input["date"] = self.adjusted_date
            elif isinstance(tool_input, str) and "date=" in tool_input:
                date_pattern = r"date=(\d{4}-\d{2}-\d{2})"
                match = re.search(date_pattern, tool_input)
                if match and match.group(1) == self.original_date:
                    new_input = tool_input.replace(f"date={self.original_date}", f"date={self.adjusted_date}")
                    action.tool_input = new_input
    
    def on_tool_end(self, output: str, **kwargs) -> None:
        """Process tool output to extract adjusted dates."""
        if isinstance(output, str) and "ADJUSTED_DATE:" in output:
            match = re.search(r"ADJUSTED_DATE:\s*(\d{4}-\d{2}-\d{2})", output)
            if match:
                self.adjusted_date = match.group(1)
                if not self.original_date:
                    original_match = re.search(r"No game found on (\d{4}-\d{2}-\d{2})", output)
                    if original_match:
                        self.original_date = original_match.group(1)

# Create the agent with tools
sync_groq_client = groq.Groq(
    api_key=GROQ_API_KEY,
    http_client=httpx.Client(follow_redirects=True)
)
async_groq_client = groq.AsyncGroq(
    api_key=GROQ_API_KEY,
    http_client=httpx.AsyncClient(follow_redirects=True)
)
llm = ChatGroq(
    model_name="llama3-70b-8192",
    api_key=GROQ_API_KEY,
    temperature=0.7,
    max_tokens=4096,
    client=sync_groq_client,
    async_client=async_groq_client
)
tools = [fetch_team_schedule, extract_team_names, fetch_team_stats, fetch_betting_trends, analyze_matchup_data, manage_memory]

# Create a callback handler for date adjustments
date_handler = DateAdjustmentHandler()

# Initialize the agent with the system prompt
agent = create_openai_tools_agent(llm, tools, prompt)

# Initialize the agent executor with the callback handler, ensuring async support
bobby_bets_agent = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=False,
    callbacks=[date_handler],
    handle_parsing_errors=True
)

async def ask_bobby(question: str, user_id: str = "default_user", sport: str = "nba") -> Dict[str, Any]:
    """Function to interact with the Bobby Bets agent with optimized execution flow and memory."""
    try:
        # Check for relevant memories using a new connection
        conn = sqlite3.connect("user_memory.db", timeout=10)
        cursor = conn.cursor()
        logger.info("Checking for previous user memories...")
        cursor.execute("SELECT memory, metadata FROM memories WHERE user_id = ?", (user_id,))
        relevant_memories = []
        team_dict = TEAM_CODES if sport == "nba" else FOOTBALL_CODES
        for row in cursor.fetchall():
            mem_text = row[0]
            mem_metadata = json.loads(row[1])
            if any(team in question.lower() for team in team_dict.keys() if team in mem_text.lower()):
                relevant_memories.append(mem_text)
        conn.close()
        
        if relevant_memories:
            logger.info(f"Found {len(relevant_memories)} relevant memories for user {user_id}")
        
        # Extract team names and confirm sport
        logger.info(f"Extracting {sport} team names...")
        teams_info = await extract_team_names.ainvoke({"text": question, "sport": sport})
        
        # If no teams found in specified sport, try the other sport
        if "error" in teams_info:
            alt_sport = "football" if sport == "nba" else "nba"
            logger.info(f"No {sport} teams found, trying {alt_sport}...")
            teams_info = await extract_team_names.ainvoke({"text": question, "sport": alt_sport})
            if "error" not in teams_info:
                sport = alt_sport
        
        if 'team1' in teams_info and 'team2' in teams_info:
            team1 = teams_info['team1']
            team2 = teams_info['team2']
            logger.info(f"Found {sport} matchup: {team1.title()} vs {team2.title()}")
        else:
            logger.info(f"No {sport} teams found, using full agent...")
            return await bobby_bets_agent.ainvoke({"input": question})
        
        # Check for date in question
        logger.info("Checking for game date...")
        date_match = re.search(r"(\d{4}-\d{1,2}-\d{1,2})", question)
        if not date_match:
            date_text_match = re.search(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})", question, re.IGNORECASE)
            if date_text_match:
                month_str, day_str, year_str = date_text_match.groups()
                month_map = {
                    "January": "01", "February": "02", "March": "03", "April": "04",
                    "May": "05", "June": "06", "July": "07", "August": "08",
                    "September": "09", "October": "10", "November": "11", "December": "12"
                }
                month_num = month_map.get(month_str.capitalize(), "01")
                day_num = day_str.zfill(2)
                date_str = f"{year_str}-{month_num}-{day_num}"
                logger.info(f"Found game date: {date_str}")
            else:
                date_str = None
                logger.info("No specific date mentioned")
        else:
            date_str = date_match.group(1)
            logger.info(f"Found game date: {date_str}")
        
        date_param = f" date={date_str}" if date_str else ""
        
        # Fetch schedule
        logger.info(f"Searching for {team1.title()} vs {team2.title()} {sport} schedule...")
        schedule_info = await fetch_team_schedule.ainvoke({"teams_and_params": f"{team1} {team2}{date_param}", "sport": sport})
        
        adjusted_date_match = re.search(r"ADJUSTED_DATE:\s*(\d{4}-\d{2}-\d{2})", schedule_info)
        adjusted_date = adjusted_date_match.group(1) if adjusted_date_match else date_str
        if adjusted_date and date_str and adjusted_date != date_str:
            logger.info(f"No {sport} game on {date_str}, using {adjusted_date}")
        
        # Fetch data in parallel
        results = {}
        logger.info(f"Gathering {sport} team stats and betting trends...")
        
        async def get_team1_stats():
            return await fetch_team_stats.ainvoke({"team_name": team1, "sport": sport})
        
        async def get_team2_stats():
            return await fetch_team_stats.ainvoke({"team_name": team2, "sport": sport})
        
        async def get_betting_trends():
            if adjusted_date:
                return await fetch_betting_trends.ainvoke({"team1": team1, "team2": team2, "date": adjusted_date, "sport": sport})
            return f"No date provided for {sport} betting trends."
        
        # Run async tasks concurrently
        team1_stats, team2_stats, betting_trends = await asyncio.gather(
            get_team1_stats(),
            get_team2_stats(),
            get_betting_trends()
        )
        results["team1_stats"] = team1_stats
        results["team2_stats"] = team2_stats
        results["betting_trends"] = betting_trends
        
        # Analyze matchup
        logger.info(f"Analyzing {sport} matchup data...")
        analysis_output = await analyze_matchup_data.ainvoke({"team1_stats": team1_stats, "team2_stats": team2_stats, "betting_trends": betting_trends, "sport": sport})
        
        # Extract sources
        schedule_source = re.search(r"URL:\s*(https?://[^\s]+)", schedule_info).group(1) if "URL:" in schedule_info else ("Basketball Reference" if sport == "nba" else "Soccerway")
        team1_source = re.search(r"URL:\s*(https?://[^\s]+)", team1_stats).group(1) if "URL:" in team1_stats else ("Basketball Reference" if sport == "nba" else "Soccerway")
        team2_source = re.search(r"URL:\s*(https?://[^\s]+)", team2_stats).group(1) if "URL:" in team2_stats else ("Basketball Reference" if sport == "nba" else "Soccerway")
        betting_source = re.search(r"Source:\s*(https?://[^\s]+)", betting_trends).group(1) if betting_trends and "Source:" in betting_trends else "Not available"
        
        # Generate final response
        bettor_prompt = f"""
I need you to analyze this {sport} matchup between {team1.title()} and {team2.title()} and provide your insights as a seasoned sports bettor.

Here's all the data I've collected:

## SCHEDULE INFO:
{schedule_info}

## TEAM 1 STATS ({team1.title()}):
{team1_stats}

## TEAM 2 STATS ({team2.title()}):
{team2_stats}

## BETTING TRENDS:
{betting_trends if betting_trends else f"No specific {sport} betting trends available."}

## ANALYSIS OUTPUT:
{analysis_output}

## SOURCE INFORMATION FOR CITATIONS:
- Schedule and Game Information: {schedule_source}
- {team1.title()} Team Statistics: {team1_source}
- {team2.title()} Team Statistics: {team2_source}
- Betting Trends: {betting_source}

Based on all this information, give me your take on this {sport} matchup as a seasoned sports bettor. Include:
1. Your prediction for the winner (or draw for football) with your confidence level.
2. Key factors influencing your prediction.
3. Notable insights you discovered.
4. Specific betting recommendations:
   - For NBA: moneyline, spread, over/under.
   - For football: 1X2, over/under goals, both teams to score (BTTS), Asian handicap.
5. Citations to the information sources.

IMPORTANT: Back up your predictions with specific data points and evidence. For example:
- NBA: "I'm taking the Celtics because they're 8-2 in their last 10 home games against teams with winning records."
- Football: "Bayern's averaging 2.5 goals per game at home, while Dortmund's defense has conceded 1.8 goals per game on the road."

Use an authentic sports bettor voice - conversational, with some slang and personality. Don't use a rigid template - make it sound natural and vary your language.
"""
        try:
            async_groq = groq.AsyncGroq(api_key=GROQ_API_KEY, http_client=httpx.AsyncClient(follow_redirects=True))
            response = await async_groq.chat.completions.create(
                model="llama3-70b-8192",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": bettor_prompt}
                ],
                temperature=0.7,
                max_tokens=4096
            )
            final_response = response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error generating {sport} bettor response: {str(e)}")
            final_response = f"""
# {team1.title()} vs {team2.title()} {sport.capitalize()} Analysis

{analysis_output}

Note: Error formatting response in sports bettor style: {str(e)}.
"""
        
        # Store analysis in memory
        logger.info(f"Saving {sport} analysis to memory...")
        try:
            conn = sqlite3.connect("user_memory.db", timeout=10)
            cursor = conn.cursor()
            team_interest = f"User showed interest in {team1.title()} vs {team2.title()} {sport} matchup"
            predicted_winner_match = re.search(r"\*\*Predicted Winner\*\*: (.*?)$", analysis_output, re.MULTILINE)
            predicted_winner = predicted_winner_match.group(1) if predicted_winner_match else "Unknown"
            confidence_level_match = re.search(r"\*\*Confidence Level\*\*: (.*?)$", analysis_output, re.MULTILINE)
            confidence_level = confidence_level_match.group(1) if confidence_level_match else "Unknown"
            prediction_memory = f"Bobby Bets predicted {predicted_winner} to win with {confidence_level} confidence"
            
            metadata = {
                "sport": sport,
                "team1": team1,
                "team2": team2,
                "predicted_winner": predicted_winner,
                "confidence_level": confidence_level
            }
            if adjusted_date:
                metadata["game_date"] = adjusted_date
            
            cursor.execute("INSERT INTO memories (user_id, memory, metadata) VALUES (?, ?, ?)",
                         (user_id, team_interest, json.dumps(metadata)))
            cursor.execute("INSERT INTO memories (user_id, memory, metadata) VALUES (?, ?, ?)",
                         (user_id, prediction_memory, json.dumps(metadata)))
            conn.commit()
        except Exception as e:
            logger.error(f"Error saving {sport} memory: {str(e)}")
        finally:
            conn.close()
        
        logger.info(f"{sport.capitalize()} analysis complete!")
        return {"output": final_response}
    except Exception as e:
        logger.error(f"Error processing {sport} question: {str(e)}")
        try:
            return await bobby_bets_agent.ainvoke({"input": question})
        except Exception as fallback_error:
            logger.error(f"Error in fallback agent execution: {str(fallback_error)}")
            return {"output": f"Error analyzing your {sport} question: {str(fallback_error)}"}
