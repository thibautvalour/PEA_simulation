import altair as alt
import numpy as np
import pandas as pd
import streamlit as st
import datetime

from data_loading_funcs import get_monthly_stock_with_dividends
from strategy import Strategy
"""
# Simulateur investissement S&P 500
"""


# Menu
col_start, col_end = st.columns(2)
with col_start:
    starting_year = st.number_input("Année de départ", 1994, 2024, 1994)
with col_end:
    ending_year = st.number_input("Année de fin d\'investissement", 1995, 2024, 2024)

col1, col2, col3 = st.columns(3)
with col1:
    initial_investment = st.number_input("Investissement Initial", min_value=0, max_value=150_000, value=1_000)
with col2:
    initial_monthly_contribution = st.number_input("Versement mensuel", min_value=0, value=100)
with col3:
    monthly_contribution_increases_per_year = st.number_input("Augmentation du versement par an",
                                                               min_value=0, max_value=500, value=0)


stock = 'SPY'
start = datetime.datetime(starting_year, 1, 1) 
end = datetime.datetime(ending_year, 1, 1) 
# # end = datetime.datetime.now() - datetime.timedelta(days=1) # Yesterday

strategy = Strategy(stock, start, end, initial_cash=initial_investment,
                    initial_monthly_contribution=initial_monthly_contribution,
                    monthly_contribution_increase_per_year=monthly_contribution_increases_per_year)


monthly_prices = get_monthly_stock_with_dividends(strategy.stock, strategy.start, strategy.end)
strategy.passive_strategy(monthly_prices)
# strategy.plot_passive_strategy(monthly_prices)

exit_value = strategy.exit_values[-1]
# print the results

fig = strategy.plot_passive_strategy(monthly_prices)
st.plotly_chart(fig, use_container_width=True)

st.write(f"Montant total investi: {strategy.invested_cash_values[-1]:,.0f}€")
st.write(f"Valeur nette de sortie: {strategy.exit_values[-1]:,.0f}€")
