import numpy as np
import pandas as pd
import yfinance as yf
import datetime

def get_monthly_stock_with_dividends(stock, start, end, yearly_fee_rate=0.00153):

        if start < datetime.datetime(1993, 3, 19):
            raise ValueError('Start date must be later than 1993-03-19')
        
        if start > end:
            raise ValueError('Start date must be earlier than end date')

        # Download historical prices and dividends
        stock_data = yf.download(stock, start=start, end=end)

        dividends = yf.Ticker(stock).dividends
        try: dividends.index = dividends.index.tz_localize(None)
        except TypeError:  pass

        dividends = dividends[(dividends.index >= start) & (dividends.index <= end)]

        # Adjust the stock prices with reinvested dividends
        adjusted_close = stock_data['Close'].copy()
        for date, dividend in dividends.items():
            adjustment_factor = 1 + dividend / adjusted_close.loc[:date].iloc[-2]
            adjusted_close.loc[date:] *= adjustment_factor
        stock_data['Adjusted Close'] = adjusted_close

        monthly_prices = stock_data.resample('MS').first()

        # Adjust the monthly prices to include the yearly fee
        monthly_fee = (1+yearly_fee_rate)**(1/12) - 1
        monthly_prices['Adjusted Close return'] = monthly_prices['Adjusted Close'].pct_change().fillna(0) - monthly_fee
        monthly_prices['cumulative_return'] = (1 + monthly_prices['Adjusted Close return']).cumprod()
        monthly_prices['Adjusted Close'] = monthly_prices['Adjusted Close'].iloc[0] * monthly_prices['cumulative_return']

        return monthly_prices
