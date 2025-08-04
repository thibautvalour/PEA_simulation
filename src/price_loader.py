from datetime import datetime
import pandas as pd
import yfinance as yf

from src.config import params
from src.utils import apply_fee_impact


class ShillerDataLoader:
    def __init__(
        self,
        start: datetime,
        end: datetime,
        include_dividends: bool = True,
        yearly_fee: float = params["SPY"]["yearly_fee"],
        normalize: bool = True,
    ):
        self.file_path = "data/shillerdata.xls"
        self.start = start
        self.end = end
        self.include_dividends = include_dividends
        self.yearly_fee = yearly_fee
        self.normalize = normalize
        validate_dates(start, end)

    def get_monthly_prices(self) -> pd.DataFrame:
        monthly_prices = self._load_and_process_data()
        if self.include_dividends:
            monthly_prices = self._compute_dividend_reinvestment(monthly_prices)
        if self.yearly_fee > 0:
            monthly_prices = apply_fee_impact(monthly_prices, self.yearly_fee)
        if self.normalize:
            # Divid by the last value to keep a purchasable price
            monthly_prices["Adjusted Close"] /= monthly_prices["Adjusted Close"].iloc[
                -1
            ]
        return monthly_prices

    def _load_and_process_data(self) -> pd.DataFrame:
        df = pd.read_excel("data/shillerdata.xls", sheet_name="Data", skiprows=7)
        df = df.drop(df.index[-1])

        df["Date"] = df["Date"].apply(
            lambda x: f"{int(x)}.{int(round((x - int(x)) * 100)):02}"
        )
        df["Date"] = pd.to_datetime(df["Date"], format="%Y.%m")

        df = (
            df.rename(columns={"P": "Close", "D": "Dividends"})
            .set_index("Date")
            .sort_index()
        )
        df = df[["Close", "Dividends"]]

        # Go to the last row where Dividends is not Nan
        last_row = df[df["Dividends"].notnull()].index[-1]
        df = df.loc[:last_row]

        df = df[(df.index > self.start) & (df.index < self.end)]

        return df

    def _compute_dividend_reinvestment(
        self, monthly_prices: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Computes an adjusted price series assuming dividends are reinvested,
        similar to how a capitalizing ETF would behave.

        Returns a new column 'Adjusted_Close' which reflects reinvested dividends.
        """
        df = monthly_prices.copy()
        adjusted_close = df["Close"].copy()

        for i in range(1, len(df)):
            prev_date = df.index[i - 1]
            dividend = df.loc[prev_date, "Dividends"]
            prev_close = adjusted_close.loc[prev_date]
            adjustment_factor = 1 + dividend / prev_close
            adjusted_close.iloc[i:] *= adjustment_factor

        df["Adjusted Close"] = adjusted_close
        return df[["Close", "Dividends", "Adjusted Close"]]


class YFStockLoader:
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

        validate_dates(start, end)

        daily_prices = yf.download(self.ticker, start=start, end=end)

        if include_dividends:
            dividends = self._get_formatted_dividends(start, end)
            daily_prices = self._compute_dividend_reinvestment(daily_prices, dividends)

        # Resample to monthly data with first day as reference
        monthly_prices = daily_prices.resample("MS").first()

        if yearly_fee > 0:
            monthly_prices = apply_fee_impact(monthly_prices, yearly_fee)

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


def validate_dates(start: datetime, end: datetime):
    """Check that starting is after creation of the stock, and start <= end"""

    # cutoff_date = datetime.strptime(params[self.ticker]["historic_start"], "%Y-%m-%d")
    # if start < cutoff_date:
    #     raise ValueError(f"Start date must be later than {cutoff_date}")

    if start > end:
        raise ValueError("Start date must be earlier than end date")


class GoldDataLoader:
    def __init__(
        self,
        start: datetime,
        end: datetime,
        yearly_fee: float = params["Gold"]["yearly_fee"],
        normalize: bool = True,
    ):
        self.file_path = "data/monthly_gold_prices.csv"
        self.start = start
        self.end = end
        self.yearly_fee = yearly_fee
        self.normalize = normalize
        validate_dates(start, end)

    def get_monthly_prices(self) -> pd.DataFrame:
        monthly_prices = self._load_and_process_data()
        if self.yearly_fee > 0:
            monthly_prices = apply_fee_impact(monthly_prices, self.yearly_fee)
        if self.normalize:
            # Divide by the last value to keep a purchasable price
            monthly_prices["Adjusted Close"] /= monthly_prices["Adjusted Close"].iloc[
                -1
            ]
        return monthly_prices

    def _load_and_process_data(self) -> pd.DataFrame:
        df = pd.read_csv(self.file_path)

        # Convert Date column to datetime
        df["Date"] = pd.to_datetime(df["Date"], format="%Y-%m")

        # Rename columns to match expected format
        df = df.rename(columns={"Price": "Close"}).set_index("Date").sort_index()

        # Filter date range (match ShillerDataLoader logic)
        df = df[(df.index > self.start) & (df.index < self.end)]

        # Gold doesn't have dividends, so create Adjusted Close column
        df["Adjusted Close"] = df["Close"]

        return df[["Close", "Adjusted Close"]]


class LivretADataLoader:
    def __init__(
        self,
        start: datetime,
        end: datetime,
        normalize: bool = True,
    ):
        self.file_path = "data/livret_A_taux.csv"
        self.start = start
        self.end = end
        self.normalize = normalize
        validate_dates(start, end)

    def get_monthly_equivalent_prices(self) -> pd.DataFrame:
        """Get monthly interest rates for Livret A"""
        monthly_prices = self._load_and_process_data()
        if self.normalize:
            # For Livret A, we'll create a cumulative value starting at 1
            monthly_prices["Adjusted Close"] = self._compute_cumulative_value(
                monthly_prices
            )
            # Normalize to last value like other assets
            monthly_prices["Adjusted Close"] /= monthly_prices["Adjusted Close"].iloc[
                -1
            ]
        return monthly_prices

    def _load_and_process_data(self) -> pd.DataFrame:
        df = pd.read_csv(self.file_path)

        # Convert Date column to datetime
        df["time_period_start"] = pd.to_datetime(
            df["time_period_start"], format="%Y-%m-%d"
        )

        # Convert French decimal format to float (comma to dot)
        df["rate"] = df["rate"].str.replace(",", ".").astype(float)

        # Convert annual rate percentage to monthly decimal
        df["monthly_rate"] = (1 + df["rate"] / 100) ** (1 / 12) - 1

        # Rename and set index
        df = df.rename(columns={"time_period_start": "Date", "rate": "Annual_Rate"})
        df = df.set_index("Date").sort_index()

        # Filter date range (match other loaders)
        df = df[(df.index > self.start) & (df.index < self.end)]

        return df[["Annual_Rate", "monthly_rate"]]

    def _compute_cumulative_value(self, monthly_rates: pd.DataFrame) -> pd.Series:
        """Compute cumulative value of 1€ invested with monthly compound interest"""
        cumulative_value = pd.Series(index=monthly_rates.index, dtype=float)
        cumulative_value.iloc[0] = 1.0

        for i in range(1, len(monthly_rates)):
            prev_value = cumulative_value.iloc[i - 1]
            monthly_rate = monthly_rates["monthly_rate"].iloc[i - 1]
            cumulative_value.iloc[i] = prev_value * (1 + monthly_rate)

        return cumulative_value
