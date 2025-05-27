from datetime import datetime
import plotly.graph_objects as go

from src.config import params


class DCAStrategy:
    def __init__(
        self,
        ticker: str,
        start: datetime,
        end: datetime,
        initial_cash: int,
        initial_monthly_contribution: int,
        yearly_bump: int,
    ):
        self.ticker = ticker
        self.start = start
        self.end = end
        self.initial_cash = initial_cash
        self.initial_monthly_contribution = initial_monthly_contribution
        self.yearly_bump = yearly_bump
        self.stock_params = params[ticker]

        # Initialize tracking lists
        self.monthly_contributions = []
        self.total_invested_cash = []
        self.portfolio_values = []
        self.exit_values = []

    def simulate_investment_strategy(self, monthly_prices):

        # Initialize portfolio
        try:
            entry_price = to_scalar(monthly_prices.iloc[0]["Adjusted Close"]) * (
                1 + self.stock_params["entry_fee"]
            )
        except:
            entry_price = monthly_prices.iloc[0]["Adjusted Close"] * (
                1 + self.stock_params["entry_fee"]
            )

        shares_owned = self.initial_cash // entry_price
        available_cash = self.initial_cash - shares_owned * entry_price

        current_monthly_contribution = self.initial_monthly_contribution

        # Start investment simulation
        for idx, (_, row) in enumerate(monthly_prices.iterrows()):

            # Increase contrib each year
            if (idx + 1) % 12 == 0:
                current_monthly_contribution += self.yearly_bump

            # Check if we can invest more in the PEA, otherwise decrease the contribution
            if self.total_invested_cash:
                potential_cash_invested = (
                    self.total_invested_cash[-1] + current_monthly_contribution
                )
                if params["Global"]["PEA_limit"] < potential_cash_invested:
                    remaining_pea_capacity = (
                        params["Global"]["PEA_limit"] - self.total_invested_cash[-1]
                    )
                    current_monthly_contribution = max(0, remaining_pea_capacity)
            # TODO: if we can't, invest in a cto

            available_cash += current_monthly_contribution

            current_price = to_scalar(row["Adjusted Close"]) * (
                1 + self.stock_params["entry_fee"]
            )
            purchasable_shares = available_cash // current_price

            shares_owned += purchasable_shares
            available_cash = available_cash - purchasable_shares * current_price

            self.monthly_contributions.append(current_monthly_contribution)
            if idx == 0:
                self.total_invested_cash.append(self.initial_cash)
            else:
                self.total_invested_cash.append(
                    self.total_invested_cash[-1] + current_monthly_contribution
                )

            portfolio_value = (
                shares_owned * to_scalar(row["Adjusted Close"]) + available_cash
            )
            self.portfolio_values.append(portfolio_value)

            exit_value = self._compute_exit_value(
                to_scalar(row["Adjusted Close"]), shares_owned, available_cash
            )
            self.exit_values.append(exit_value)

    def _compute_exit_value(self, stock_price, shares_owned, available_cash):
        current_selling_price = stock_price * (1 - self.stock_params["exit_fee"])
        exit_value_before_tax = (shares_owned * current_selling_price) + available_cash

        capital_gain = exit_value_before_tax - self.total_invested_cash[-1]

        if capital_gain <= 0:  # No gain -> No tax
            exit_value_after_tax = exit_value_before_tax
        else:
            exit_value_after_tax = (
                capital_gain * (1 - params["Global"]["exit_tax_rate"])
                + self.total_invested_cash[-1]
            )
        return exit_value_after_tax

    def create_portfolio_visualization(self, monthly_prices):

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=monthly_prices.index,
                y=self.total_invested_cash,
                mode="lines",
                name="Montant total investi",
                line=dict(color="royalblue", width=2, dash="dash"),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=monthly_prices.index,
                y=self.exit_values,
                mode="lines",
                name="Valeur de sortie",
                line=dict(color="green", width=2),
            )
        )
        fig.update_layout(
            # title=f"Strategy: {self.start.year}-{self.end.year}",
            xaxis_title="Année",
            yaxis_title="Valeur ($)",
            legend=dict(xanchor="left", yanchor="top", x=0.01, y=0.95),
            yaxis=dict(range=[0, max(self.exit_values) * 1.15]),
            font=dict(family="Courier New, monospace", size=14, color="#7f7f7f"),
        )

        return fig


def to_scalar(x):
    return x.item() if hasattr(x, "item") else x
