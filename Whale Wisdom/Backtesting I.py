import os
import requests
import time
import hmac
import hashlib
import base64
import json
from datetime import datetime, timedelta
from tqdm import tqdm
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

TRADING_DAYS = 252

# A constant return series yields ~1e-18 rather than exactly 0 after arithmetic,
# so an `== 0` test is not enough to catch a degenerate Sharpe denominator.
MIN_STD = 1e-12


def _load_dotenv_if_available():
    """Load a local .env file if python-dotenv is installed. Optional."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv()


def _require_env(name):
    value = os.environ.get(name)
    if not value:
        raise SystemExit(
            f"Missing required environment variable: {name}\n"
            f"Copy .env.example to .env, fill in your own WhaleWisdom API keys, "
            f"and re-run. (.env is git-ignored.)"
        )
    return value


# Function to generate API signature
def generate_signature(args, timestamp, secret_key):
    message = f"{args}\n{timestamp}"
    signature = hmac.new(secret_key.encode(), message.encode(), hashlib.sha1).digest()
    return base64.b64encode(signature).decode()


# Function to get WhaleWisdom data
def get_whale_wisdom_data(api_url):
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        data = response.json()
        return data
    except (requests.exceptions.HTTPError, requests.exceptions.RequestException, json.JSONDecodeError) as err:
        print(f"Request error occurred: {err}")
        return None


def fetch_data(shared_access_key, secret_access_key):
    """Fetch holdings for a list of filers and save them to JSON."""
    # List of known filer IDs to fetch data for
    filer_ids = [216, 3562, 5888, 46800, 68960, 111617, 116228, 173707, 192800, 193730, 2506, 4807, 6021, 11343, 88475, 20, 221, 254, 756, 3420, 3573, 3595, 4112, 4288, 4821, 4855, 5469, 277616, 299848]

    all_data = []

    start_date = datetime.strptime('2015-01-01', '%Y-%m-%d')
    end_date = datetime.strptime('2024-01-01', '%Y-%m-%d')
    delta = timedelta(days=365)  # Each request covers one year of data

    for filer_id in tqdm(filer_ids, desc="Fetching data for filers"):
        current_date = start_date
        while current_date < end_date:
            next_date = current_date + delta
            args = json.dumps({
                "command": "holdings",
                "filer_ids": [filer_id],
                "include_13d": 1,
                "start_date": current_date.strftime('%Y-%m-%d'),
                "end_date": next_date.strftime('%Y-%m-%d')
            })

            timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
            api_sig = generate_signature(args, timestamp, secret_access_key)
            api_url = f"https://whalewisdom.com/shell/command.json?args={args}&api_shared_key={shared_access_key}&api_sig={api_sig}&timestamp={timestamp}"

            data = get_whale_wisdom_data(api_url)
            if data and 'results' in data:
                all_data.extend(data['results'])
            else:
                print(f"Skipping filer ID {filer_id} due to errors.")
                break  # Skip to next filer ID if there's an error

            current_date = next_date
            time.sleep(1)  # Avoid hitting API rate limits

    if all_data:
        with open('whale_wisdom_data.json', 'w') as json_file:
            json.dump({"results": all_data}, json_file, indent=4)
        print("Data saved to whale_wisdom_data.json")
    else:
        print("No data to save.")


def clean_and_save_data():
    with open('whale_wisdom_data.json', 'r') as f:
        data = json.load(f)

    valid_records = []
    for result in data['results']:
        for record in result['records']:
            if 'holdings' in record:
                for holding in record['holdings']:
                    holding.update({
                        'date_last_filed': record['date_last_filed'],
                        'quarter': record['quarter']
                    })
                    valid_records.append(holding)

    if not valid_records:
        print("No valid records found.")
        return

    records = pd.DataFrame(valid_records)
    records.dropna(inplace=True)
    records['quarter_date'] = pd.to_datetime(records['date_last_filed'], errors='coerce')

    records.sort_values(by='quarter_date', inplace=True)
    records.to_csv('cleaned_holdings.csv', index=False)
    print("Data cleaned and saved to cleaned_holdings.csv")

    unique_quarters = records['quarter_date'].unique()
    train_size = int(len(unique_quarters) * 0.7)
    train_quarters = unique_quarters[:train_size]
    test_quarters = unique_quarters[train_size:]

    train_data = records[records['quarter_date'].isin(train_quarters)]
    test_data = records[records['quarter_date'].isin(test_quarters)]

    train_data.to_csv('train_holdings.csv', index=False)
    test_data.to_csv('test_holdings.csv', index=False)
    print(f"Number of training samples: {len(train_data)}")
    print(f"Number of testing samples: {len(test_data)}")


def _metrics_from_returns(returns):
    """Return performance metrics for a return series.

    NOTE ON ANNUALISATION: the rows in this dataset are quarterly 13F filings,
    but the annualisation below uses TRADING_DAYS (252), as the original
    revision did. That treats quarterly observations as daily ones and inflates
    both CAGR and the Sharpe ratio. The figures are left on the original basis
    so they stay comparable with the previously reported results — see the
    README note — but they should not be read as true annualised numbers.
    """
    returns = returns.dropna()
    if returns.empty:
        return {'total_return': np.nan, 'cagr': np.nan, 'sharpe': np.nan,
                'max_drawdown': np.nan, 'equity': pd.Series(dtype=float)}

    equity = (1 + returns).cumprod()
    total_return = equity.iloc[-1] - 1
    cagr = ((1 + total_return) ** (TRADING_DAYS / len(returns))) - 1
    std = returns.std()
    sharpe = (returns.mean() / std * np.sqrt(TRADING_DAYS)
              if np.isfinite(std) and std > MIN_STD else np.nan)
    max_drawdown = (equity / equity.cummax() - 1).min()

    return {'total_return': total_return, 'cagr': cagr, 'sharpe': sharpe,
            'max_drawdown': max_drawdown, 'equity': equity}


def backtest_and_save_results():
    data = pd.read_csv('cleaned_holdings.csv', parse_dates=['date_last_filed'])
    data = data.sort_values('date_last_filed')

    # Create a new column for the strategy signal
    data['signal'] = 0

    # Implementing a strategy
    data['zscore'] = (data['current_percent_of_portfolio'] - data['current_percent_of_portfolio'].rolling(20).mean()) / data['current_percent_of_portfolio'].rolling(20).std()
    data.loc[data['zscore'] < -1.5, 'signal'] = 1  # Buy signal
    data.loc[data['zscore'] > 1.5, 'signal'] = -1  # Sell signal

    data['position'] = data['signal'].shift()
    data['daily_return'] = data.groupby('stock_ticker')['avg_price'].pct_change()
    data['strategy_return'] = data['position'] * data['daily_return']

    # Metrics are now computed on the strategy's own returns. The previous
    # revision recomputed daily_return inside calculate_metrics() and reported
    # those numbers under the "Strategy" label, so it was actually reporting
    # buy-and-hold while claiming to report the strategy.
    strategy = _metrics_from_returns(data['strategy_return'])
    portfolio = _metrics_from_returns(data['daily_return'])

    print("Strategy (z-score mean reversion):")
    print(f"  Total Return: {strategy['total_return']:.2f}")
    print(f"  CAGR:         {strategy['cagr']:.2f}")
    print(f"  Sharpe Ratio: {strategy['sharpe']:.2f}")
    print(f"  Max Drawdown: {strategy['max_drawdown']:.2f}")
    print("Buy-and-hold portfolio (for comparison):")
    print(f"  Total Return: {portfolio['total_return']:.2f}")
    print(f"  CAGR:         {portfolio['cagr']:.2f}")
    print(f"  Sharpe Ratio: {portfolio['sharpe']:.2f}")
    print(f"  Max Drawdown: {portfolio['max_drawdown']:.2f}")

    # Plotting results — each curve now carries the label that matches the
    # series actually plotted.
    plt.figure(figsize=(10, 6))
    plt.plot(data['date_last_filed'], strategy['equity'], label='Strategy Return')
    plt.plot(data['date_last_filed'], portfolio['equity'], label='Portfolio Value')
    plt.xlabel('Date')
    plt.ylabel('Cumulative Return')
    plt.title('Backtesting Results')
    plt.legend()
    plt.savefig('backtesting_results.png')
    plt.close()
    print("Plot saved to backtesting_results.png")

    # Persist the per-row results, which the README documents as an output.
    data.to_csv('backtesting_results.csv', index=False)
    print("Per-row results saved to backtesting_results.csv")


def main():
    _load_dotenv_if_available()
    shared_access_key = _require_env('WHALEWISDOM_SHARED_ACCESS_KEY')
    secret_access_key = _require_env('WHALEWISDOM_SECRET_ACCESS_KEY')

    fetch_data(shared_access_key, secret_access_key)
    clean_and_save_data()
    backtest_and_save_results()


if __name__ == "__main__":
    main()