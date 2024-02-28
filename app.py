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

starting_year = st.slider("Année de départ", 1994, 2024, 1994)
ending_year = st.slider("Année de fin d\'investissement", 1994, 2024, 2024)

initial_investment = st.number_input("Investment Initial", 0, 100_000, 1000)
initial_monthly_contribution = st.number_input("Versement mensuelle", 0, 1000, 100)
monthly_contribution_increases_per_year = st.number_input("Augmentation du versement par an", 0, 500, 100)

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
