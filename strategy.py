import pandas as pd 
import plotly.graph_objects as go

from data_loading_funcs import get_monthly_stock_with_dividends

class Strategy:
    def __init__(self, stock, start, end, 
                 initial_cash, initial_monthly_contribution, monthly_contribution_increase_per_year,
                 entry_fee=0.03, exit_fee=0.03, yearly_fee=0.00153,
                 exit_taxe_rate_on_gains=0.172, limit_PEA=160_500):
        self.stock = stock
        self.start = start
        self.end = end
        self.entry_fee = entry_fee
        self.exit_fee = exit_fee
        self.yearly_fee = yearly_fee
        self.exit_taxe_rate_on_gains = exit_taxe_rate_on_gains
        self.initial_cash = initial_cash
        self.initial_monthly_contribution = initial_monthly_contribution
        self.monthly_contribution_increase_per_year = monthly_contribution_increase_per_year
        self.limit_PEA = limit_PEA

    
    def passive_strategy(self, monthly_prices):

        shares_owned = self.initial_cash // (monthly_prices.iloc[0]['Adjusted Close'] * (1 + self.entry_fee))
        current_cash = self.initial_cash - (shares_owned * monthly_prices.iloc[0]['Adjusted Close']* (1 + self.entry_fee))
        current_monthly_contribution = self.initial_monthly_contribution

        # Lists to store value over time for plotting
        portfolio_values, exit_values = [], []
        monthly_contributions, invested_cash_values = [], []

        for idx, (_, row) in enumerate(monthly_prices.iterrows()):

            if (idx+1)%12 == 0:
                current_monthly_contribution += self.monthly_contribution_increase_per_year
       
            # Check if we can invest more in the PEA
            if invested_cash_values and (invested_cash_values[-1] + current_monthly_contribution > self.limit_PEA):
                current_monthly_contribution = max(0, self.limit_PEA - invested_cash_values[-1])

            current_cash += current_monthly_contribution
            
            # Buy as many shares as possible
            shares_to_buy = current_cash // (row['Adjusted Close'] * (1 + self.entry_fee))
            shares_owned += shares_to_buy
            current_cash = current_cash - (shares_to_buy * row['Adjusted Close'] * (1 + self.entry_fee))
            
            
            monthly_contributions.append(current_monthly_contribution)
            invested_cash_values.append((invested_cash_values[-1] + current_monthly_contribution) if idx>0
                                         else self.initial_cash)
            
            # Stock value
            portfolio_values.append(shares_owned * row['Adjusted Close'] + current_cash)

            # Compute potential exit value
            money_after_selling = shares_owned * row['Adjusted Close'] * (1 - self.exit_fee) + current_cash
            if money_after_selling < invested_cash_values[-1]: # No gain so no tax
                exit_value = money_after_selling
            else:
                exit_value = ((money_after_selling - invested_cash_values[-1]) * (1 - self.exit_taxe_rate_on_gains) 
                                + invested_cash_values[-1])
            exit_values.append(exit_value)


        self.montly_contributions = monthly_contributions
        self.invested_cash_values = invested_cash_values
        self.portfolio_values = portfolio_values
        self.exit_values = exit_values

    def plot_passive_strategy(self, monthly_prices):

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=monthly_prices.index, y=self.invested_cash_values,
                                mode='lines', name="Montant total investi",
                                line=dict(color='royalblue', width=2, dash='dash')))
        fig.add_trace(go.Scatter(x=monthly_prices.index, y=self.exit_values,
                                mode='lines', name="Valeur de sortie",
                                line=dict(color='green', width=2)))

        fig.update_layout(
            # title=f"Dollar-Cost Averaging Strategy: {self.start.year}-{self.end.year}",
            xaxis_title="Année", yaxis_title="Valeur ($)",
            legend=dict(xanchor="left", yanchor="top", x=0.01, y=0.95),
            yaxis=dict(range=[0, max(self.exit_values)*1.15]),
            # yaxis_type="log",
            font=dict(
                family="Courier New, monospace",
                size=14, color="#7f7f7f"))
        
        return fig

    def run(self):
        monthly_prices = get_monthly_stock_with_dividends(self.stock, self.start, self.end,
                                                          yearly_fee_rate=self.yearly_fee)
        self.passive_strategy(monthly_prices)
        self.plot_passive_strategy(monthly_prices)
