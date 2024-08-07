# -*- coding: utf-8 -*-
"""KeyMetric version I testing.

Originally prototyped in Colab. The `!pip install yfinance` magic line has been
removed — it is a Colab-only directive and is a SyntaxError in a .py file.
Install the dependency normally instead:

    pip install yfinance pandas
"""

import numpy as np
import pandas as pd
import yfinance as yf

# A constant return series yields ~1e-18 rather than exactly 0 after arithmetic,
# so an `== 0` test is not enough to catch a degenerate Sharpe denominator.
MIN_STD = 1e-12


def calculate_return(prices, periods):
    return prices.pct_change(periods=periods)


def calculate_cagr(prices, years):
    initial_value = prices.iloc[0]
    final_value = prices.iloc[-1]
    cagr = (final_value / initial_value) ** (1 / years) - 1
    return cagr


def calculate_max_drawdown(prices):
    roll_max = prices.cummax()
    daily_drawdown = prices / roll_max - 1.0
    max_drawdown = daily_drawdown.cummin().min()
    return max_drawdown


def calculate_beta(stock_returns, market_returns):
    covariance = stock_returns.cov(market_returns)
    variance = market_returns.var()
    beta = covariance / variance
    return beta


def calculate_alpha(stock_returns, market_returns, risk_free_rate, beta):
    market_excess_return = market_returns.mean() - risk_free_rate
    stock_excess_return = stock_returns.mean() - risk_free_rate
    alpha = stock_excess_return - beta * market_excess_return
    return alpha


def calculate_sharpe_ratio(returns, risk_free_rate):
    excess_returns = returns - risk_free_rate
    average_excess_return = excess_returns.mean()
    standard_deviation = excess_returns.std()
    # A constant series yields ~1e-18 rather than exactly 0, so guard on a
    # tolerance instead of an equality test; otherwise this returns a huge
    # finite number rather than the NaN it should.
    if not np.isfinite(standard_deviation) or standard_deviation < MIN_STD:
        return np.nan
    return average_excess_return / standard_deviation


def analyze_stock(stock_ticker, market_ticker, risk_free_rate, output_file_path,
                  start_date="2020-07-01", end_date="2024-07-04"):
    # Fetch data
    stock_data = yf.download(stock_ticker, start=start_date, end=end_date, progress=False)
    market_data = yf.download(market_ticker, start=start_date, end=end_date, progress=False)

    # Ensure the data frames have the same date range
    df = stock_data[['Close']].join(market_data[['Close']], lsuffix='_Stock', rsuffix='_Market').dropna()

    # Calculate returns
    df['Stock_Return_1d'] = calculate_return(df['Close_Stock'], 1)
    df['Stock_Return_30d'] = calculate_return(df['Close_Stock'], 30)
    df['Stock_Return_1y'] = calculate_return(df['Close_Stock'], 252)  # Approximate number of trading days in a year

    # Calculate CAGR
    years = len(df) / 252  # Approximate number of trading days in a year
    df['CAGR'] = calculate_cagr(df['Close_Stock'], years)

    # Calculate Max Drawdown
    df['Max_Drawdown'] = calculate_max_drawdown(df['Close_Stock'])

    # Calculate Beta
    df['Market_Return'] = df['Close_Market'].pct_change()
    df['Beta'] = calculate_beta(df['Stock_Return_1d'].dropna(), df['Market_Return'].dropna())

    # Calculate Alpha
    beta_value = df['Beta'].iloc[-1]  # Use the most recent beta value
    df['Alpha'] = calculate_alpha(df['Stock_Return_1d'].dropna(), df['Market_Return'].dropna(), risk_free_rate, beta_value)

    # Calculate Sharpe Ratio
    df['Sharpe_Ratio'] = calculate_sharpe_ratio(df['Stock_Return_1d'].dropna(), risk_free_rate)

    # Persist the results — the previous revision accepted output_file_path but
    # never wrote to it, so the committed analysis_results.csv came from an
    # earlier version of this script.
    df.to_csv(output_file_path)

    latest = df.iloc[-1]
    print(f"{stock_ticker} vs {market_ticker}: {len(df)} rows ({df.index[0].date()} to {df.index[-1].date()})")
    print(f"  CAGR:          {latest['CAGR']:.2%}")
    print(f"  Max drawdown:  {latest['Max_Drawdown']:.2%}")
    print(f"  Beta:          {latest['Beta']:.3f}")
    print(f"  Alpha:         {latest['Alpha']:.5f}")
    print(f"  Sharpe ratio:  {latest['Sharpe_Ratio']:.3f}")
    return df


def main():
    stock_ticker = 'ANF'          # Replace with your stock ticker
    market_ticker = 'SPY'         # Replace with your market index ticker (S&P 500 index)
    risk_free_rate = 0.02 / 252   # Daily risk-free rate
    output_file_path = 'analysis_results.csv'

    analyze_stock(stock_ticker, market_ticker, risk_free_rate, output_file_path)
    print(f"Analysis results saved to {output_file_path}")


if __name__ == "__main__":
    main()