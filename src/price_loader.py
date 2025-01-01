import yfinance as yf
from datetime import datetime
import pandas as pd

from src.config import params


class StockLoader:
    """Class to get stock prices with some preprocessing"""

    def __init__(self, ticker: str):
        self.ticker = ticker
        self.stock = yf.Ticker(ticker)

    def get_monthly_prices(
        self,
        start: datetime,
        end: datetime,
        yearly_fee: float = 0,
        include_dividends: bool = False,
    ) -> pd.DataFrame:
        """
        Get monthly stock prices with optional dividend reinvestment and fees

        Args:
            start: Start date
            end: End date
            yearly_fee: Annual fee as decimal (e.g., 0.001 for 0.1%)
            include_dividends: Whether to include dividend reinvestment

        Returns:
            DataFrame with monthly stock prices,

        If yearly_fee or include_dividends, relevant price is 'Adjusted Close'
        """
        print(type(start))
        self._validate_dates(start, end)

        # Get daily prices
        daily_prices = yf.download(self.ticker, start=start, end=end)

        if include_dividends:
            dividends = self._get_formatted_dividends(start, end)
            daily_prices = self._compute_dividend_reinvestment(daily_prices, dividends)

        # Resample to monthly data with first day as reference
        monthly_prices = daily_prices.resample("MS").first()

        if yearly_fee > 0:
            monthly_prices = self._apply_fee_impact(monthly_prices, yearly_fee)

        return monthly_prices

    def _get_formatted_dividends(self, start: datetime, end: datetime) -> pd.Series:
        """Get and format dividend data for the specified period"""
        dividends = self.stock.dividends
        dividends.index = pd.to_datetime(dividends.index, errors="coerce")

        try:  # Handle timezone
            dividends.index = dividends.index.tz_localize(None)
        except TypeError:
            pass

        # Filter date range
        dividends = dividends[(dividends.index >= start) & (dividends.index <= end)]

        return dividends

    def _compute_dividend_reinvestment(
        self, prices: pd.DataFrame, dividends: pd.Series
    ) -> pd.DataFrame:
        """Calculate prices with dividend reinvestment"""
        adjusted_close = prices["Close"].copy()

        for date, dividend in dividends.items():
            # Calculate adjustment factor based on previous day's close
            prev_close = adjusted_close.loc[:date].iloc[-2]
            adjustment_factor = 1 + dividend / prev_close
            # Apply adjustment to all subsequent prices
            adjusted_close.loc[date:] *= adjustment_factor

        prices["Adjusted Close"] = adjusted_close
        return prices

    def _apply_fee_impact(
        self, monthly_prices: pd.DataFrame, yearly_fee: float
    ) -> pd.DataFrame:
        """Apply fee impact to monthly prices"""
        # Convert annual fee to monthly
        monthly_fee = (1 + yearly_fee) ** (1 / 12) - 1

        # Calculate returns with fee impact
        returns = monthly_prices["Adjusted Close"].pct_change().fillna(0) - monthly_fee

        # Update prices based on cumulative returns
        monthly_prices["Cumulative Return"] = (1 + returns).cumprod()
        monthly_prices["Adjusted Close"] = (
            monthly_prices["Adjusted Close"].iloc[0]
            * monthly_prices["Cumulative Return"]
        )

        return monthly_prices

    def _validate_dates(self, start: datetime, end: datetime):
        """Check that starting is after creation of the stock, and start <= end"""

        cutoff_date = datetime.strptime(
            params[self.ticker]["historic_start"], "%Y-%m-%d"
        )
        if start < cutoff_date:
            raise ValueError(f"Start date must be later than {cutoff_date}")

        if start > end:
            raise ValueError("Start date must be earlier than end date")
