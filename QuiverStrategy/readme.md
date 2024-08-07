# KeyMetric VersionI Testing

This repository contains a Python script designed for testing various financial metrics, such as returns, CAGR, max drawdown, beta, alpha, and Sharpe ratio for a given stock. The script uses historical stock data and market index data fetched using the `yfinance` library.

## Features

- **Calculate Stock Returns**: Daily, 30-day, and yearly percentage change in stock prices.
- **CAGR (Compound Annual Growth Rate)**: Measure the growth rate of the stock over a specified period.
- **Max Drawdown**: The maximum observed loss from a peak to a trough.
- **Beta**: Measure the volatility of the stock in relation to the market.
- **Alpha**: The stock's performance relative to the market, adjusted for risk.
- **Sharpe Ratio**: Evaluate the risk-adjusted return of the stock.

## Installation

To run the script, ensure you have Python installed, along with the necessary libraries:

```bash
pip install yfinance pandas
```

## Usage

To use the script, specify the stock ticker, market index ticker, and the risk-free rate. The script fetches the historical data, calculates the metrics, and saves the results in a CSV file.

```python
# Example usage
stock_ticker = 'ANF'  # Replace with your stock ticker
market_ticker = 'SPY'  # Replace with your market index ticker (S&P 500 index)
risk_free_rate = 0.02 / 252  # Daily risk-free rate
output_file_path = 'analysis_results.csv'  # Output CSV file path

analyze_stock(stock_ticker, market_ticker, risk_free_rate, output_file_path)
```

The output file `analysis_results.csv` will contain the calculated metrics for the specified stock.

## Script Details

- `calculate_return(prices, periods)`: Calculates percentage return over specified periods.
- `calculate_cagr(prices, years)`: Calculates the CAGR based on historical prices.
- `calculate_max_drawdown(prices)`: Determines the maximum drawdown.
- `calculate_beta(stock_returns, market_returns)`: Computes the beta of the stock.
- `calculate_alpha(stock_returns, market_returns, risk_free_rate, beta)`: Calculates alpha using the stock and market returns.
- `calculate_sharpe_ratio(returns, risk_free_rate)`: Calculates the Sharpe ratio.
