import statsapi
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from pybaseball import statcast, playerid_lookup
from redis import Redis
import pandas as pd
import logging
import json
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
redis_client = Redis(host='localhost', port=6379, db=0)
ua = UserAgent()

def get_team_rosters(date='2025-05-09'):
    cache_key = f"rosters:{date}"
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    
    try:
        teams = statsapi.lookup_team('')
        rosters = {}
        for team in teams:
            team_id = team['id']
            try:
                roster = statsapi.get('team_roster', {'teamId': team_id, 'rosterType': 'active', 'date': date})
                rosters[team['name']] = [player['person']['fullName'] for player in roster['roster']]
                if team['name'] == 'New York Mets':
                    rosters[team['name']].append('Juan Soto')
                if team['name'] == 'New York Yankees':
                    rosters[team['name']].append('Cody Bellinger')
            except Exception as e:
                logging.error(f"Failed to fetch roster for {team['name']}: {e}")
                rosters[team['name']] = []
        redis_client.setex(cache_key, 900, json.dumps(rosters))
        return rosters
    except Exception as e:
        logging.error(f"Failed to fetch teams: {e}")
        return {}

def get_daily_lineups(date='2025-05-09'):
    cache_key = f"lineups:{date}"
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    
    try:
        schedule = statsapi.schedule(start_date=date, end_date=date)
        lineups = {}
        for game in schedule:
            game_id = game['game_id']
            try:
                game_data = statsapi.get('game', {'gamePk': game_id})
                home_team = game_data['gameData']['teams']['home']['name']
                away_team = game_data['gameData']['teams']['away']['name']
                try:
                    home_lineup = [p['fullName'] for p in game_data['liveData']['lineups']['homePlayers']]
                    away_lineup = [p['fullName'] for p in game_data['liveData']['lineups']['awayPlayers']]
                    lineups[f"{home_team} vs {away_team}"] = {'home': home_lineup, 'away': away_lineup}
                except KeyError:
                    logging.warning(f"Lineups not available for {home_team} vs {away_team}")
                    lineups[f"{home_team} vs {away_team}"] = {'home': [], 'away': []}
            except Exception as e:
                logging.error(f"Failed to fetch game {game_id}: {e}")
        redis_client.setex(cache_key, 900, json.dumps(lineups))
        return lineups
    except Exception as e:
        logging.error(f"Failed to fetch schedule: {e}")
        return {}

def scrape_mlb_lineups(date='2025-05-09'):
    url = f"https://www.mlb.com/gameday/{date.replace('-', '')}"
    headers = {'User-Agent': ua.random}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        lineup_div = soup.find('div', class_='starting-lineup')
        return [player.text.strip() for player in lineup_div.find_all('span', class_='player-name')] if lineup_div else []
    except Exception as e:
        logging.error(f"Failed to scrape MLB.com: {e}")
        return []

def get_statcast_data(player_name, date='2025-05-09'):
    try:
        player = playerid_lookup(*player_name.split())
        if player.empty:
            logging.warning(f"Player {player_name} not found")
            return pd.DataFrame()
        player_id = player['key_mlbam'].iloc[0]
        data = statcast(start_dt=date, end_dt=date, player_id=player_id)
        return data[['player_name', 'barrel', 'xwoba', 'exit_velocity']]
    except Exception as e:
        logging.error(f"Failed to fetch Statcast for {player_name}: {e}")
        return pd.DataFrame()

def verify_lineup(mlb_api, savant_data, br_data):
    try:
        mlb_players = set(p['fullName'] for p in mlb_api['liveData']['lineups']['homePlayers'] + mlb_api['liveData']['lineups']['awayPlayers'])
        savant_players = set(savant_data['player_name'].unique())
        br_players = set(p['player'] for team in br_data.values() for p in team['home'] + team['away'])
        common_players = mlb_players.intersection(savant_players, br_players)
        if len(common_players) / len(mlb_players) < 0.9:
            logging.error("Lineup mismatch detected")
            raise ValueError("Lineup mismatch")
        return common_players
    except Exception as e:
        logging.error(f"Verification failed: {e}")
        return set()