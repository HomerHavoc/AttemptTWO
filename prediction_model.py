import pandas as pd
import numpy as np
from overlays.weather import get_weather_factor
from overlays.park import get_park_factor
from data_fetcher import fetch_player_stats

def get_daily_predictions():
    players = fetch_player_stats()
    predictions = []

    for player in players:
        base_hr_prob = player['barrel_rate'] * 0.03 + player['launch_angle_score'] * 0.02
        weather_adj = get_weather_factor(player['game_id'])
        park_adj = get_park_factor(player['ballpark'])

        final_prob = base_hr_prob * weather_adj * park_adj
        predictions.append({
            "Player": player["name"],
            "Team": player["team"],
            "HR_Probability": round(final_prob, 4)
        })

    return pd.DataFrame(predictions).sort_values(by="HR_Probability", ascending=False)