"""
# Simulateur investissement PEA
"""

import datetime
import time
import streamlit as st
import plotly.graph_objects as go

from src.config import params
from src.price_loader import (
    YFStockLoader,
    ShillerDataLoader,
    GoldDataLoader,
    LivretADataLoader,
)
from src.strategies import DCAStrategy, GoldDCAStrategy, LivretAStrategy


st.set_page_config(page_icon=":money_with_wings:")
st.title("Simulation d'investissement récurrent (DCA)")

# Hide Streamlit options and style buttons
hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            
            /* Style buttons to be blue by default */
            .stButton > button {
                background-color: #0066cc !important;
                color: white !important;
                border: none !important;
            }
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# Menu
col_start, col_end = st.columns(2)
with col_start:
    starting_year = st.number_input("Année de départ (1871-2024)", 1871, 2025, 1994)
with col_end:
    ending_year = st.number_input(
        "Année de fin d'investissement (1872-2025)", 1871, 2025, 2024
    )

# Ensure the end year is after the start year
if ending_year < starting_year:
    st.error("L'année de fin doit être supérieure à l'année de départ.")

col_fisc, col_init = st.columns(2)
with col_fisc:
    taxation_mode = st.selectbox(
        "Fiscalité",
        ["PEA", "Aucune"],
        help="PEA : les plus-values sont taxées à 17,2 % jusqu’à 150 k€, puis à 30 % au-delà. Aucune : pas de taxation.",
    )
    # Set max investment based on taxation mode

with col_init:
    initial_investment = st.number_input(
        "Investissement Initial (\$)",
        min_value=0,
        value=10_000,
    )


col_monthly, col_yearly = st.columns(2)
with col_monthly:
    initial_monthly_contribution = st.number_input(
        "Versement mensuel (\$)", min_value=0, value=100
    )
with col_yearly:
    yearly_bump = st.number_input(
        "Chaque année, le versement mensuel augmente de :",
        min_value=0,
        max_value=10_000,
        value=0,
    )

if st.button("Lancer la simulation"):

    with st.spinner("Calcul en cours..."):

        time.sleep(1)  # Simulate some processing time
        start = datetime.datetime(starting_year, 1, 1)
        end = datetime.datetime(ending_year, 1, 1)

        # Check if Livret A is available for the selected start year
        livret_a_start_year = int(params["Livret A"]["historic_start"][:4])
        include_livret_a = starting_year >= livret_a_start_year

        # SPY Strategy
        spy_strategy = DCAStrategy(
            "SPY",
            start,
            end,
            initial_cash=int(initial_investment),
            initial_monthly_contribution=int(initial_monthly_contribution),
            yearly_bump=int(yearly_bump),
            taxation_mode=taxation_mode,
        )
        spy_monthly_prices = ShillerDataLoader(
            start, end, include_dividends=True, yearly_fee=params["SPY"]["yearly_fee"]
        ).get_monthly_prices()
        spy_strategy.simulate_investment_strategy(spy_monthly_prices)

        # Gold Strategy
        gold_strategy = GoldDCAStrategy(
            start,
            end,
            initial_cash=int(initial_investment),
            initial_monthly_contribution=int(initial_monthly_contribution),
            yearly_bump=int(yearly_bump),
            taxation_mode=taxation_mode,
        )
        gold_monthly_prices = GoldDataLoader(
            start, end, yearly_fee=params["Gold"]["yearly_fee"]
        ).get_monthly_prices()
        gold_strategy.simulate_investment_strategy(gold_monthly_prices)

        # Livret A Strategy (only if available for the selected period)
        if include_livret_a:
            livret_a_strategy = LivretAStrategy(
                start,
                end,
                initial_cash=int(initial_investment),
                initial_monthly_contribution=int(initial_monthly_contribution),
                yearly_bump=int(yearly_bump),
            )
            livret_a_monthly_rates = LivretADataLoader(start, end).get_monthly_rates()
            livret_a_strategy.simulate_investment_strategy(livret_a_monthly_rates)

    # Create combined visualization
    fig = go.Figure()

    # Add invested cash baseline (same for both strategies)
    fig.add_trace(
        go.Scatter(
            x=spy_monthly_prices.index,
            y=spy_strategy.total_invested_cash,
            mode="lines",
            name="Montant total investi",
            line=dict(color="royalblue", width=2, dash="dash"),
        )
    )

    # Add strategies to plot
    spy_strategy.add_to_plot(fig, spy_monthly_prices, "S&P500", "green")
    gold_strategy.add_to_plot(fig, gold_monthly_prices, "Or", "gold")
    if include_livret_a:
        livret_a_strategy.add_to_plot(fig, livret_a_monthly_rates, "Livret A", "lightblue")

    # Update layout
    exit_values_list = [
        max(spy_strategy.exit_values),
        max(gold_strategy.exit_values),
    ]
    if include_livret_a:
        exit_values_list.append(max(livret_a_strategy.exit_values))
    max_value = max(exit_values_list)
    fig.update_layout(
        xaxis_title="Année",
        yaxis_title="Valeur ($)",
        legend=dict(xanchor="left", yanchor="top", x=0.01, y=0.95),
        yaxis=dict(range=[0, max_value * 1.15]),
        font=dict(family="Courier New, monospace", size=14, color="#7f7f7f"),
    )

    # Display results
    total_invested = spy_strategy.total_invested_cash[-1]
    spy_exit = spy_strategy.exit_values[-1]
    gold_exit = gold_strategy.exit_values[-1]

    st.metric("Montant investi", f"{total_invested:,.0f} $")

    if include_livret_a:
        livret_a_exit = livret_a_strategy.exit_values[-1]
        col1, col2, col3 = st.columns(3)
        with col1:
            st.subheader("📈 S&P500")
            st.metric("Valeur de sortie", f"{spy_exit:,.0f} $")
            spy_return = ((spy_exit / total_invested) - 1) * 100
            st.metric("Rendement total", f"{spy_return:.1f}%")

        with col2:
            st.subheader("🥇 Or")
            st.metric("Valeur de sortie", f"{gold_exit:,.0f} $")
            gold_return = ((gold_exit / total_invested) - 1) * 100
            st.metric("Rendement total", f"{gold_return:.1f}%")

        with col3:
            st.subheader("🏦 Livret A", help="Aucune fiscalité")
            st.metric("Valeur de sortie", f"{livret_a_exit:,.0f} $")
            livret_a_return = ((livret_a_exit / total_invested) - 1) * 100
            st.metric("Rendement total", f"{livret_a_return:.1f}%")
    else:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📈 S&P500")
            st.metric("Valeur de sortie", f"{spy_exit:,.0f} $")
            spy_return = ((spy_exit / total_invested) - 1) * 100
            st.metric("Rendement total", f"{spy_return:.1f}%")

        with col2:
            st.subheader("🥇 Or")
            st.metric("Valeur de sortie", f"{gold_exit:,.0f} $")
            gold_return = ((gold_exit / total_invested) - 1) * 100
            st.metric("Rendement total", f"{gold_return:.1f}%")
            
        st.info(f"Le Livret A n'est pas disponible pour les simulations commençant avant {livret_a_start_year}.")

    st.plotly_chart(fig)

    # Show warnings based on taxation mode
    if taxation_mode == "PEA" and (total_invested > params["Global"]["PEA_limit"]):
        st.warning(
            "Plafond PEA atteint durant la stratégie. Les plus-values des investissements au-delà de ce montant ont été taxées à 30%."
        )

    # Simple taxation explanation
    if taxation_mode == "PEA":
        st.caption(
            f"Fiscalité : {params['Global']['exit_tax_rate']*100:.1f}% sur les plus-values des placements jusqu'à {params['Global']['PEA_limit']:,}$, puis {params['Global']['taxable_account_tax_rate']*100:.0f}% au-delà. Livret A sans fiscalité."
        )
    else:
        st.caption(
            "Fiscalité : Aucune taxe sur les plus-values. Livret A sans fiscalité."
        )
