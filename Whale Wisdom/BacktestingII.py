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


# Fetch and save data
def fetch_data(shared_access_key, secret_access_key):
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


# Clean and save data
def clean_data():
    with open('whale_wisdom_data.json', 'r') as f:
        data = json.load(f)

    all_records = []
    for result in data['results']:
        for record in result['records']:
            holdings = record.get('holdings', [])
            for holding in holdings:
                holding.update({
                    'date_last_filed': record.get('date_last_filed'),
                    'quarter': record.get('quarter')
                })
                all_records.append(holding)

    df = pd.DataFrame(all_records)
    df.dropna(inplace=True)
    df['date_last_filed'] = pd.to_datetime(df['date_last_filed'])
    df.sort_values('date_last_filed', inplace=True)

    df.to_csv('cleaned_holdings.csv', index=False)
    print("Data cleaned and saved to 'cleaned_holdings.csv'.")


# Inspect data (optional step)
def inspect_data():
    df = pd.read_csv('cleaned_holdings.csv')
    print(df.head())
    print(df.columns)


# Calculate Z-Score
def calculate_zscore(data, window=20):
    data['mean'] = data['daily_return'].rolling(window).mean()
    data['std'] = data['daily_return'].rolling(window).std()
    data['zscore'] = (data['daily_return'] - data['mean']) / data['std']
    return data


# Implement strategy
def implement_strategy(data):
    data['signal'] = 0
    data.loc[data['zscore'] < -1.5, 'signal'] = 1  # Buy signal
    data.loc[data['zscore'] > 1.5, 'signal'] = -1  # Sell signal
    data['position'] = data['signal'].shift().fillna(0)
    return data


# Calculate metrics
def calculate_metrics(data):
    """Compute strategy and buy-and-hold metrics.

    NOTE ON ANNUALISATION: rows here are quarterly 13F filings, but returns are
    annualised with TRADING_DAYS (252) as the original revision did. That treats
    quarterly observations as daily ones and overstates CAGR and Sharpe. The
    basis is unchanged so results stay comparable with earlier runs, but these
    are not true annualised figures.
    """
    data['daily_return'] = data.groupby('stock_ticker')['price'].pct_change()
    data = data.dropna(subset=['daily_return'])  # Drop NaN values after pct_change

    data = calculate_zscore(data)
    data = implement_strategy(data)

    data['strategy_return'] = data['position'] * data['daily_return']

    # Compound the strategy returns. The previous revision summed them
    # (cumsum), which is not a total return.
    strategy_equity = (1 + data['strategy_return']).cumprod()
    portfolio_equity = (1 + data['daily_return']).cumprod()

    total_return = strategy_equity.iloc[-1] - 1
    cagr = ((1 + total_return) ** (TRADING_DAYS / len(data))) - 1 if total_return > -1 else np.nan

    strategy_std = data['strategy_return'].std()
    sharpe_ratio = (data['strategy_return'].mean() / strategy_std * np.sqrt(TRADING_DAYS)
                    if np.isfinite(strategy_std) and strategy_std > MIN_STD else np.nan)

    # Percentage drawdown of the strategy equity curve. The previous revision
    # returned (price.cummax() - price).max(), an absolute dollar amount on the
    # raw price series rather than a drawdown of the strategy.
    max_drawdown = (strategy_equity / strategy_equity.cummax() - 1).min()

    return total_return, cagr, sharpe_ratio, max_drawdown, data, strategy_equity, portfolio_equity


# Backtesting
def backtest():
    data = pd.read_csv('cleaned_holdings.csv').copy()
    data['price'] = data['avg_price']
    data['date_last_filed'] = pd.to_datetime(data['date_last_filed'])

    (total_return, cagr, sharpe_ratio, max_drawdown,
     data, strategy_equity, portfolio_equity) = calculate_metrics(data)

    print(f"Total Return: {total_return}")
    print(f"CAGR: {cagr}")
    print(f"Sharpe Ratio: {sharpe_ratio}")
    print(f"Max Drawdown: {max_drawdown}")

    # Plotting
    data['cumulative_return'] = strategy_equity.values
    data['portfolio_value'] = portfolio_equity.values

    plt.figure(figsize=(10, 6))
    plt.plot(data['date_last_filed'], data['cumulative_return'], label='Strategy Return')
    plt.plot(data['date_last_filed'], data['portfolio_value'], label='Portfolio Value')
    plt.xlabel('Date')
    plt.ylabel('Cumulative Return')
    plt.title('Backtesting Results')
    plt.legend()
    plt.savefig('backtesting_results2.png')
    plt.close()

    # Save strategy returns
    data.to_csv('backtesting_results.csv', index=False)
    print("Backtesting results saved to 'backtesting_results.csv'.")


def main():
    _load_dotenv_if_available()
    shared_access_key = _require_env('WHALEWISDOM_SHARED_ACCESS_KEY')
    secret_access_key = _require_env('WHALEWISDOM_SECRET_ACCESS_KEY')

    fetch_data(shared_access_key, secret_access_key)
    clean_data()
    # inspect_data()  # Uncomment this line if you want to inspect the data
    backtest()


if __name__ == "__main__":
    main()