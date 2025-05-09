from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
from data_fetcher import get_team_rosters, get_daily_lineups
from bvp_spider import run_bvp_spider

with DAG('mlb_pipeline', start_date=datetime(2025, 5, 9), schedule_interval='*/15 * * * *') as dag:
    fetch_rosters = PythonOperator(task_id='fetch_rosters', python_callable=get_team_rosters)
    fetch_lineups = PythonOperator(task_id='fetch_lineups', python_callable=get_daily_lineups)
    scrape_bvp = PythonOperator(task_id='scrape_bvp', python_callable=run_bvp_spider)
    fetch_rosters >> fetch_lineups >> scrape_bvp