# Stock and Bitcoin Data Scraper

This script scrapes financial data for specific stocks and Bitcoin, processes the data to generate various metrics, and visualizes the results in graphs. The script can also save the processed data to CSV files for further analysis.

## Features

- Scrapes current stock price and market capitalization data from `bitcointreasuries.net`.
- Fetches historical stock and Bitcoin price data using the `yfinance` library.
- Calculates various financial metrics, including BTC ratio, NAV premium, and BTC per share.
- Generates time-series graphs to visualize BTC ratio, NAV premium, and BTC per share over different periods.
- Saves the combined and historical data to CSV files.

## Requirements

- Python 3.x
- Required Python packages:
  - `requests`
  - `beautifulsoup4`
  - `yfinance`
  - `pandas`
  - `numpy`
  - `matplotlib`
  - `tqdm`

You can install the required packages using pip:

```bash
pip install requests beautifulsoup4 yfinance pandas numpy matplotlib tqdm
```

## Usage

1. **Update the stock information:**

   Edit the `stocks` list in the `main()` function to include the stocks you want to analyze. Each stock entry should include the name, symbol, and a unique identifier for scraping.

2. **Run the script:**

   Run the script using the following command:

   ```bash
   python your_script_name.py
   ```

   The script will scrape the required data, process it, and save the results to `combined_data.csv` and `historical_combined_data.csv`.

3. **View the graphs:**

   The script generates several graphs showing the BTC ratio, NAV premium, and BTC per share over the last 7, 30, and 90 days. These graphs are saved as PNG files.

4. **Check the CSV files:**

   - `combined_data.csv`: Contains the latest combined data for the stocks processed.
   - `historical_combined_data.csv`: Contains historical data by appending new data to the existing file.

## Functions

- `scrape_current_price(url, selector)`: Scrapes the current price of a stock from the provided URL using a CSS selector.
- `scrape_market_cap(url)`: Scrapes the market capitalization of a stock.
- `scrape_btc_cap(url)`: Scrapes the total Bitcoin market cap from CoinMarketCap.
- `get_stock_volume(ticker_symbol)`: Fetches the volume of a stock for the last trading day.
- `fetch_data(ticker, date)`: Fetches the stock and Bitcoin close prices for a given date.
- `process_stock(stock_info)`: Processes the stock information and calculates various financial metrics.
- `plot_graphs(result_df, symbol)`: Plots and saves the graphs for the financial metrics.
- `main()`: Main function that controls the flow of the script.

## Notes

- Ensure that the CSS selectors and URLs in the scraping functions are correct and up-to-date.
- The script includes basic error handling, but you may need to modify it for your specific use case.
- The script uses tqdm for progress indication; it is advisable to run it in a terminal that supports ASCII or Unicode characters.
