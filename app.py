import os
from dotenv import load_dotenv
import numpy as np
import pandas as pd
import streamlit as st
import datetime
import altair as alt
# from langchain.llms import OpenAI
from openai import OpenAI

from data_loading_funcs import get_monthly_stock_with_dividends
from strategy import Strategy


load_dotenv()  # take environment variables from .env.
# api_key = os.getenv('OPENAI_API_KEY')
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

# LLM Part

st.title('🦜 LLM 🦜')

client = OpenAI()

def generate_response(input_text, conversation_history):
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=conversation_history + [{"role": "user", "content": input_text}],
        temperature=0.8,
    )
    return completion.choices[0].message.content

# Initialize conversation_history in session state if it doesn't exist
if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []

with st.form('my_form'):
    text = st.text_area('Enter text:', 'Hello world!')
    submitted = st.form_submit_button('Submit')
    if submitted:
        response = generate_response(text, st.session_state.conversation_history)
        st.session_state.conversation_history.append({"role": "user", "content": text})
        st.session_state.conversation_history.append({"role": "assistant", "content": response})
        st.info(response)
