"""Backtester for Dollar-Cost Averaging (DCA) investment strategies"""

# pylint: disable=import-error

import datetime
import time
import streamlit as st
import plotly.graph_objects as go

from src.config import params
from src.price_loader import (
    ShillerDataLoader,
    GoldDataLoader,
    LivretADataLoader,
)
from src.strategies import DCAStrategy, GoldDCAStrategy, LivretAStrategy
from src.utils import compute_global_return, compute_geometric_mean_return


st.title("Simulation d'investissement récurrent (DCA)")

st.set_page_config(page_icon=":money_with_wings:")

# Hide Streamlit options and style buttons
HIDE_STREAMLIT_STYLE = """
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
st.markdown(HIDE_STREAMLIT_STYLE, unsafe_allow_html=True)

# Menu
col_start, col_end = st.columns(2)
with col_start:
    starting_year = st.number_input("Année de départ (1871-2024)", 1871, 2025, 1994)
with col_end:
    ending_year = st.number_input(
        "Année de fin d'investissement (1872-2025)", 1871, 2025, 2024
    )

# Ensure the end year is after the start year
n_years = ending_year - starting_year
if n_years < 1:
    st.error("L'année de fin doit être supérieure à l'année de départ.")

col_fisc, col_init = st.columns(2)
with col_fisc:
    taxation_mode = st.selectbox(
        "Fiscalité",
        ["PEA", "Aucune"],
        help="PEA : les plus-values sont taxées à 17,2 % jusqu'à 150 k€, "
        "puis à 30 % au-delà. Aucune : pas de taxation.",
    )

with col_init:
    initial_investment = st.number_input(
        "Investissement Initial ($)",
        min_value=0,
        value=10_000,
    )


col_monthly, col_yearly = st.columns(2)
with col_monthly:
    initial_monthly_contribution = st.number_input(
        "Versement mensuel ($)", min_value=0, value=100
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
        time.sleep(0.5)  # Simulate some processing time, UI looks smarter
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
            initial_cash=initial_investment,
            initial_monthly_contribution=initial_monthly_contribution,
            yearly_bump=yearly_bump,
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
            initial_cash=initial_investment,
            initial_monthly_contribution=initial_monthly_contribution,
            yearly_bump=yearly_bump,
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
                initial_cash=initial_investment,
                initial_monthly_contribution=initial_monthly_contribution,
                yearly_bump=yearly_bump,
            )
            livret_a_monthly_equivalent_prices = LivretADataLoader(
                start, end
            ).get_monthly_equivalent_prices()
            livret_a_strategy.simulate_investment_strategy(
                livret_a_monthly_equivalent_prices
            )

    # Compute metrics
    total_invested = spy_strategy.total_invested_cash[-1]
    spy_exit = spy_strategy.exit_values[-1]
    gold_exit = gold_strategy.exit_values[-1]
    spy_return = compute_global_return(spy_exit, total_invested)
    gold_return = compute_global_return(gold_exit, total_invested)
    spy_average_return = compute_geometric_mean_return(spy_return, n_years)
    gold_average_return = compute_geometric_mean_return(gold_return, n_years)
    if include_livret_a:
        livret_a_exit = livret_a_strategy.exit_values[-1]
        livret_a_return = compute_global_return(livret_a_exit, total_invested)
        livret_a_average_return = compute_geometric_mean_return(
            livret_a_return, n_years
        )

    # Plot
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=spy_monthly_prices.index,
            y=spy_strategy.total_invested_cash,
            mode="lines",
            name="Montant total investi",
            line={"color": "royalblue", "width": 2, "dash": "dash"},
        )
    )
    spy_strategy.add_to_plot(fig, "S&P500", "green")
    gold_strategy.add_to_plot(fig, "Or", "gold")
    if include_livret_a:
        livret_a_strategy.add_to_plot(fig, "Livret A", "lightblue")

    # compute max value for y-axis
    max_value = max(
        *spy_strategy.exit_values,
        *gold_strategy.exit_values,
        *(livret_a_strategy.exit_values if include_livret_a else []),
    )
    # update y axis range
    fig.update_layout(
        xaxis_title="Année",
        yaxis_title="Valeur ($)",
        legend={"xanchor": "left", "yanchor": "top", "x": 0.01, "y": 0.95},
        yaxis={"range": [0, max_value * 1.15]},
        font={"family": "Courier New, monospace", "size": 14, "color": "#7f7f7f"},
    )

    st.metric("Montant investi", f"{total_invested:,.0f} $")

    cols = st.columns(3 if include_livret_a else 2)
    cols[0].subheader("📈 S&P500")
    cols[0].metric("Valeur de sortie", f"{spy_exit:,.0f} $")
    cols[0].metric("Rendement total", f"{(spy_return * 100):.1f}%")
    cols[0].metric("Rendement annuel moyen", f"{spy_average_return:.1%}")
    cols[1].subheader("🥇 Or")
    cols[1].metric("Valeur de sortie", f"{gold_exit:,.0f} $")
    cols[1].metric("Rendement total", f"{(gold_return * 100):.1f}%")
    cols[1].metric("Rendement annuel moyen", f"{gold_average_return:.1%}")
    if include_livret_a:
        cols[2].subheader("🏦 Livret A", help="Aucune fiscalité")
        cols[2].metric("Valeur de sortie", f"{livret_a_exit:,.0f} $")
        cols[2].metric("Rendement total", f"{(livret_a_return * 100):.1f}%")
        cols[2].metric("Rendement annuel moyen", f"{livret_a_average_return:.1%}")
    else:
        st.info(
            f"Le Livret A n'est pas disponible pour les simulations "
            f"commençant avant {livret_a_start_year}."
        )

    st.plotly_chart(fig)

    # Show warnings based on taxation mode
    if taxation_mode == "PEA" and (total_invested > params["Global"]["PEA_limit"]):
        st.warning(
            "Plafond PEA atteint durant la stratégie. Les plus-values des "
            "investissements au-delà de ce montant ont été taxées à 30%."
        )

    # Simple taxation explanation
    if taxation_mode == "PEA":
        st.caption(
            f"Fiscalité : {params['Global']['exit_tax_rate']*100:.1f}% sur les "
            f"plus-values des placements jusqu'à {params['Global']['PEA_limit']:,}$, "
            f"puis {params['Global']['taxable_account_tax_rate']*100:.0f}% au-delà. "
            "Livret A sans fiscalité."
        )
    else:
        st.caption(
            "Fiscalité : Aucune taxe sur les plus-values. Livret A sans fiscalité."
        )
