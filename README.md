# PEA Investment Simulator

Investment simulation tool comparing Dollar Cost Averaging strategies across S&P 500, Gold, and Livret A with French taxation rules.

## Overview

Simulates long-term investment strategies using historical data (1871-2025) with realistic costs, fees, and PEA tax modeling.

**Assets:**
- S&P 500: Shiller data with dividends, 3% entry/exit fees, 0.153% annual
- Gold: World Bank prices, 0.25% annual storage fee
- Livret A: Banque de France rates, no fees

**Data Sources:**
- S&P 500: [Yale University](http://www.econ.yale.edu/~shiller/data.htm)
- Gold: [World Bank](https://datahub.io/core/gold-prices)
- Livret A: [Banque de France](https://webstat.banque-france.fr/fr/catalogue/mir1/MIR1.M.FR.B.L23FRLA.D.R.A.2230U6.EUR.O)

**Tax Modes:**
- PEA: Gains are taxed at 17.2% social contributions, up to a maximum investment of €150,000; above this, gains are subject to a 30% flat tax.
- No Tax: Theoretical comparison

## Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
```
