# Program I: Financial Metrics Calculation

## Overview

This Python script fetches, processes, and analyzes financial data from Seeking Alpha and Yahoo Finance. The program is designed to calculate various financial metrics, including Compound Annual Growth Rate (CAGR) and Sharpe Ratio, for a set of selected stocks ("Our Picks") as well as other financial assets like Treasury Bills, Gold, Silver, and major indices (Nasdaq, S&P 500).

## Features

- **Data Fetching**: Retrieves current and closed picks data from Seeking Alpha and historical data from Yahoo Finance.
- **Data Processing**: Cleans and processes the raw data to extract relevant financial information.
- **CAGR Calculation**: Computes the CAGR for selected assets over a specified period.
- **Sharpe Ratio Calculation**: Calculates the Sharpe Ratio to assess the risk-adjusted return of selected assets.
- **Weighted Metrics Calculation**: Calculates weighted CAGR and Sharpe Ratio for the selected stocks based on their holding percentages.
- **Data Storage**: Saves processed data and calculated financial metrics to CSV files for further analysis.

## Requirements

- Python 3.x
- pandas
- requests
- yfinance
- numpy

You can install the required packages using pip:

```bash
pip install pandas requests yfinance numpy
```

## Usage

1. **Login to Seeking Alpha**:
    - Replace the placeholder email and password in the `login_data` dictionary with your Seeking Alpha credentials.
2. **Run the Script**:
    - Execute the script to log in, fetch data, process it, and calculate financial metrics.
3. **Results**:
    - The results are saved into `current_alpha_picks.csv`, `closed_alpha_picks.csv`, and `financial_metrics.csv`.

## Files

- **`current_alpha_picks.csv`**: Contains data on currently active stock picks from Seeking Alpha.
- **`closed_alpha_picks.csv`**: Contains data on closed stock picks from Seeking Alpha.
- **`financial_metrics.csv`**: Contains the calculated CAGR and Sharpe Ratios for selected assets.

## Notes

- Ensure that your Seeking Alpha credentials are valid and have the necessary access to fetch data.
- Modify the asset tickers and parameters in the script as needed to suit your analysis requirements.


# Program II: Stock Average Volume Calculation

## Overview

This Python script fetches historical stock data from Yahoo Finance and calculates various average trading volumes, including the last day's trading volume, 10-day average, 30-day average, and 3-month average for a list of selected stocks.

## Features

- **Data Fetching**: Retrieves historical stock data for the past six months from Yahoo Finance.
- **Volume Calculation**: Calculates the last day trading volume, 10-day average volume, 30-day average volume, and 3-month average volume for each stock.
- **Data Storage**: Saves the calculated volumes to a CSV file for further analysis.

## Requirements

- Python 3.x
- pandas
- yfinance

You can install the required packages using pip:

```bash
pip install pandas yfinance
```

## Usage

1. **Define Tickers**:
    - The list of stock tickers is predefined in the script. You can modify this list to include any other tickers you wish to analyze.
2. **Run the Script**:
    - Execute the script to fetch data and calculate average volumes for the specified tickers.
3. **Results**:
    - The results are saved into `average_volumes.csv`.

## Files

- **`average_volumes.csv`**: Contains the calculated average trading volumes for the specified stock tickers.

## Notes

- Ensure a stable internet connection as the script fetches data from Yahoo Finance.
- Modify the list of tickers to include any other stocks you want to analyze.

