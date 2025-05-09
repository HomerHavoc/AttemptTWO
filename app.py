import streamlit as st
from prediction_model import get_daily_predictions
from data_fetcher import fetch_today_matchups
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="MLB Home Run Predictor", layout="wide")

st.title("MLB Home Run Probability Predictor")

# Load data
matchups = fetch_today_matchups()
predictions = get_daily_predictions()

st.subheader("Predicted Top HR Hitters Today")
st.dataframe(predictions)

# Plot predictions
fig = px.bar(predictions.head(20), x='Player', y='HR_Probability', color='Team', title='Top 20 HR Probabilities')
st.plotly_chart(fig, use_container_width=True)