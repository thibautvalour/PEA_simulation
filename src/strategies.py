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
        taxation_mode: str = "PEA",
    ):
        self.ticker = ticker
        self.start = start
        self.end = end
        self.initial_cash = initial_cash
        self.initial_monthly_contribution = initial_monthly_contribution
        self.yearly_bump = yearly_bump
        self.taxation_mode = taxation_mode
        self.params = params[ticker]

        self.monthly_contributions = []
        self.total_invested_cash = []
        self.portfolio_values = []
        self.exit_values = []
        self.pea_invested = []
        self.taxable_invested = []
        self.pea_shares = []
        self.taxable_shares = []

    def simulate_investment_strategy(self, monthly_prices):
        entry_price = self._get_entry_price(monthly_prices)
        pea_cash, taxable_cash, pea_shares, taxable_shares = self._init_accounts(
            entry_price
        )
        monthly_contrib = self.initial_monthly_contribution

        for idx, (_, row) in enumerate(monthly_prices.iterrows()):
            if (idx + 1) % 12 == 0:
                monthly_contrib += self.yearly_bump

            pea_contrib, taxable_contrib = self._split_contribution(
                monthly_contrib, idx, pea_cash, taxable_cash
            )
            pea_cash += pea_contrib
            taxable_cash += taxable_contrib

            price = to_scalar(row["Adjusted Close"]) * (1 + self.params["entry_fee"])
            new_pea_shares, new_taxable_shares = self._buy_shares(
                price, pea_cash, taxable_cash
            )

            pea_shares += new_pea_shares
            taxable_shares += new_taxable_shares
            pea_cash -= new_pea_shares * price
            taxable_cash -= new_taxable_shares * price

            self._track_values(monthly_contrib, pea_contrib, taxable_contrib, idx)

            stock_price = to_scalar(row["Adjusted Close"])
            portfolio_val = self._calc_portfolio_value(
                stock_price, pea_shares, taxable_shares, pea_cash, taxable_cash
            )
            exit_val = self._calc_exit_value(
                stock_price, pea_shares, taxable_shares, pea_cash, taxable_cash, idx
            )

            self.portfolio_values.append(portfolio_val)
            self.exit_values.append(exit_val)

    def _get_entry_price(self, monthly_prices):
        try:
            return to_scalar(monthly_prices.iloc[0]["Adjusted Close"]) * (
                1 + self.params["entry_fee"]
            )
        except:
            return monthly_prices.iloc[0]["Adjusted Close"] * (
                1 + self.params["entry_fee"]
            )

    def _init_accounts(self, entry_price):
        if self.taxation_mode == "PEA":
            pea_initial = min(self.initial_cash, params["Global"]["PEA_limit"])
            taxable_initial = self.initial_cash - pea_initial
        else:
            pea_initial = 0
            taxable_initial = self.initial_cash

        pea_shares = pea_initial // entry_price if pea_initial > 0 else 0
        taxable_shares = taxable_initial // entry_price if taxable_initial > 0 else 0
        pea_cash = pea_initial - pea_shares * entry_price
        taxable_cash = taxable_initial - taxable_shares * entry_price

        return pea_cash, taxable_cash, pea_shares, taxable_shares

    def _split_contribution(self, monthly_contrib, idx, pea_cash, taxable_cash):
        if self.taxation_mode != "PEA":
            return 0, monthly_contrib

        current_pea_invested = self.pea_invested[-1] if self.pea_invested else 0
        remaining_capacity = max(
            0, params["Global"]["PEA_limit"] - current_pea_invested
        )
        pea_contrib = min(monthly_contrib, remaining_capacity)
        return pea_contrib, monthly_contrib - pea_contrib

    def _buy_shares(self, price, pea_cash, taxable_cash):
        if price <= 0:
            return 0, 0
        return pea_cash // price, taxable_cash // price

    def _track_values(self, monthly_contrib, pea_contrib, taxable_contrib, idx):
        self.monthly_contributions.append(monthly_contrib)

        # Add initial cash to first calculation
        initial_pea = (
            self.initial_cash
            if self.taxation_mode == "Aucune"
            else min(self.initial_cash, params["Global"]["PEA_limit"])
        )
        initial_taxable = (
            0
            if self.taxation_mode == "Aucune"
            else max(0, self.initial_cash - params["Global"]["PEA_limit"])
        )

        if self.taxation_mode == "PEA":
            base_pea = initial_pea if not self.pea_invested else 0
            base_taxable = initial_taxable if not self.taxable_invested else 0
        else:
            base_pea = 0
            base_taxable = self.initial_cash if not self.taxable_invested else 0

        current_pea = (
            (self.pea_invested[-1] if self.pea_invested else 0) + pea_contrib + base_pea
        )
        current_taxable = (
            (self.taxable_invested[-1] if self.taxable_invested else 0)
            + taxable_contrib
            + base_taxable
        )

        self.pea_invested.append(current_pea)
        self.taxable_invested.append(current_taxable)
        self.total_invested_cash.append(current_pea + current_taxable)

    def _calc_portfolio_value(
        self, stock_price, pea_shares, taxable_shares, pea_cash, taxable_cash
    ):
        return (pea_shares + taxable_shares) * stock_price + pea_cash + taxable_cash

    def _calc_exit_value(
        self, stock_price, pea_shares, taxable_shares, pea_cash, taxable_cash, idx
    ):
        sell_price = stock_price * (1 - self.params["exit_fee"])

        pea_value = pea_shares * sell_price + pea_cash
        pea_invested_amt = self.pea_invested[idx] if self.pea_invested else 0
        pea_gain = pea_value - pea_invested_amt
        pea_exit = self._apply_tax(pea_value, pea_gain, pea_invested_amt, "pea")

        taxable_value = taxable_shares * sell_price + taxable_cash
        taxable_invested_amt = (
            self.taxable_invested[idx] if self.taxable_invested else 0
        )
        taxable_gain = taxable_value - taxable_invested_amt
        taxable_exit = self._apply_tax(
            taxable_value, taxable_gain, taxable_invested_amt, "taxable"
        )

        return pea_exit + taxable_exit

    def _apply_tax(self, value, gain, invested, account_type):
        if gain <= 0 or self.taxation_mode == "Aucune":
            return value

        if account_type == "pea":
            tax_rate = params["Global"]["exit_tax_rate"]
        else:
            tax_rate = params["Global"]["taxable_account_tax_rate"]

        return gain * (1 - tax_rate) + invested

    def add_to_plot(self, fig, monthly_prices, strategy_name=None, color="green"):
        name = strategy_name or f"Valeur de sortie ({self.ticker})"
        fig.add_trace(
            go.Scatter(
                x=monthly_prices.index,
                y=self.exit_values,
                mode="lines",
                name=name,
                line=dict(color=color, width=2),
            )
        )
        return fig

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
        fig = self.add_to_plot(fig, monthly_prices, color="green")

        fig.update_layout(
            xaxis_title="Année",
            yaxis_title="Valeur ($)",
            legend=dict(xanchor="left", yanchor="top", x=0.01, y=0.95),
            yaxis=dict(range=[0, max(self.exit_values) * 1.15]),
            font=dict(family="Courier New, monospace", size=14, color="#7f7f7f"),
        )
        return fig


class GoldDCAStrategy(DCAStrategy):
    def __init__(
        self,
        start: datetime,
        end: datetime,
        initial_cash: int,
        initial_monthly_contribution: int,
        yearly_bump: int,
        taxation_mode: str = "PEA",
    ):
        super().__init__(
            "Gold",
            start,
            end,
            initial_cash,
            initial_monthly_contribution,
            yearly_bump,
            taxation_mode,
        )

    def add_to_plot(self, fig, monthly_prices, strategy_name=None, color="gold"):
        name = strategy_name or "Valeur de sortie (Or)"
        return super().add_to_plot(fig, monthly_prices, name, color)


class LivretAStrategy:
    def __init__(
        self,
        start: datetime,
        end: datetime,
        initial_cash: int,
        initial_monthly_contribution: int,
        yearly_bump: int,
    ):
        self.ticker = "Livret A"
        self.start = start
        self.end = end
        self.initial_cash = initial_cash
        self.initial_monthly_contribution = initial_monthly_contribution
        self.yearly_bump = yearly_bump

        self.monthly_contributions = []
        self.total_invested_cash = []
        self.portfolio_values = []
        self.exit_values = []

    def simulate_investment_strategy(self, monthly_rates):
        cash = float(self.initial_cash)
        shares = 0
        monthly_contrib = self.initial_monthly_contribution

        for idx, (_, row) in enumerate(monthly_rates.iterrows()):
            if (idx + 1) % 12 == 0:
                monthly_contrib += self.yearly_bump

            actual_contrib = monthly_contrib

            cash += actual_contrib

            # Buy shares with available cash (using normalized Adjusted Close price)
            price = row["Adjusted Close"]
            if price > 0:
                new_shares = cash / price
                shares += new_shares
                cash = 0  # All cash converted to shares

            self.monthly_contributions.append(actual_contrib)
            total_invested = (
                self.total_invested_cash[-1]
                if self.total_invested_cash
                else self.initial_cash
            ) + actual_contrib
            self.total_invested_cash.append(total_invested)

            # Portfolio value = shares * current price + remaining cash
            portfolio_value = shares * price + cash
            self.portfolio_values.append(portfolio_value)
            self.exit_values.append(portfolio_value)

    def add_to_plot(self, fig, monthly_rates, strategy_name=None, color="lightblue"):
        name = strategy_name or "Livret A"
        fig.add_trace(
            go.Scatter(
                x=monthly_rates.index,
                y=self.exit_values,
                mode="lines",
                name=name,
                line=dict(color=color, width=2),
            )
        )
        return fig

    def create_portfolio_visualization(self, monthly_rates):
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=monthly_rates.index,
                y=self.total_invested_cash,
                mode="lines",
                name="Montant total investi",
                line=dict(color="royalblue", width=2, dash="dash"),
            )
        )
        fig = self.add_to_plot(fig, monthly_rates, color="lightblue")

        fig.update_layout(
            xaxis_title="Année",
            yaxis_title="Valeur ($)",
            legend=dict(xanchor="left", yanchor="top", x=0.01, y=0.95),
            yaxis=dict(range=[0, max(self.exit_values) * 1.15]),
            font=dict(family="Courier New, monospace", size=14, color="#7f7f7f"),
        )
        return fig


def to_scalar(x):
    return x.item() if hasattr(x, "item") else x
