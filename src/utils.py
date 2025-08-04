import pandas as pd


def compute_global_return(exit_value, investment):
    return (exit_value - investment) / investment


def compute_geometric_mean_return(global_return, n_years):
    return (global_return + 1) ** (1 / n_years) - 1


def apply_fee_impact(monthly_prices: pd.DataFrame, yearly_fee: float) -> pd.DataFrame:
    """Apply fee impact to monthly prices"""

    monthly_fee = (1 + yearly_fee) ** (1 / 12) - 1

    # Calculate returns with fee impact
    returns = monthly_prices["Adjusted Close"].pct_change().fillna(0) - monthly_fee

    # Update prices based on cumulative returns
    monthly_prices["Cumulative Return"] = (1 + returns).cumprod()
    monthly_prices["Adjusted Close"] = (
        monthly_prices["Adjusted Close"].iloc[0] * monthly_prices["Cumulative Return"]
    )

    return monthly_prices
