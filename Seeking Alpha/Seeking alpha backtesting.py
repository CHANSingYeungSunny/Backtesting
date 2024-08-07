"""Seeking Alpha pick-portfolio backtest.

Scrapes the current and closed picks from Seeking Alpha, then compares the
holding-weighted performance of the pick portfolio against seven liquid
benchmark assets on CAGR and annualised Sharpe ratio.

Credentials come from the environment — see .env.example.
"""

import os
import json
import requests
import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime, timedelta

# A single, consistent annual risk-free rate used for every Sharpe ratio.
#
# The previous revision carried a per-asset `risk_free_rates` dict whose values
# were badly mis-scaled (0.0027 for 3-month T-bills, 0.0996 for silver), which
# produced an implausible 15.0 Sharpe for TBIL. Subtracting a *different*
# risk-free rate from each asset also made the column incomparable across rows,
# defeating the point of a benchmark table.
RISK_FREE_RATE = 0.0524

TRADING_DAYS = 252

# Below this daily standard deviation the ratio is numerically meaningless.
# A constant return series yields ~1e-18 rather than exactly 0 after
# subtracting the risk-free rate, so an `== 0` test is not enough.
MIN_STD = 1e-12

SHARPE_START = '2023-07-01'
SHARPE_END = '2024-07-01'


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
            f"Copy .env.example to .env, fill in your own Seeking Alpha credentials, "
            f"and re-run. (.env is git-ignored.)"
        )
    return value


# --------------------------------------------------------------------------
# Seeking Alpha scraping
# --------------------------------------------------------------------------

def fetch_data(url, session, headers):
    response = session.get(url, headers=headers)
    if response.status_code == 200:
        return json.loads(response.text)
    else:
        print(f"获取数据失败，状态码: {response.status_code}")
        return None


def process_data(data, included):
    stock_data = []
    for pick in data:
        attributes = pick['attributes']
        relationships = pick['relationships']
        ticker_id = relationships['ticker']['data']['id']
        ticker_info = included.get(ticker_id, {}).get('attributes', {})
        sector_id = ticker_info.get('sector', {}).get('data', {}).get('id', '')
        sector_info = included.get(sector_id, {}).get('attributes', {})

        holding = ticker_info.get('holding', None)
        if holding is not None:
            holding = float(holding) * 100  # 转换为百分比
        else:
            holding = 'N/A'

        stock_data.append([
            pick['id'],
            attributes['buy_price'],
            attributes['sell_price'],
            attributes.get('total_return'),
            attributes.get('price_return'),
            attributes['created_at'],
            attributes['removed_at'],
            attributes['article_title'],
            ticker_id,
            ticker_info.get('slug', ''),
            ticker_info.get('companyName', ''),
            sector_info.get('name', ''),
            ticker_info.get('rating', 'N/A'),
            holding
        ])
    return stock_data


def scrape_seeking_alpha_picks(email, password):
    """Fetch the current and closed picks and write both to CSV."""
    session = requests.Session()

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Content-Type': 'application/json',
        'Accept': '*/*',
        'Origin': 'https://seekingalpha.com',
        'Referer': 'https://seekingalpha.com/',
    }

    login_url = 'https://seekingalpha.com/api/v3/login_tokens'
    login_data = {
        'data': {
            'type': 'loginTokens',
            'relationships': {
                'user': {
                    'data': {
                        'email': email,
                        'password': password
                    }
                }
            }
        }
    }

    response = session.post(login_url, json=login_data, headers=headers)
    if response.status_code != 201:
        print(f"登录失败。状态码: {response.status_code}")
        return False

    print("登录成功!")
    current_url = 'https://seekingalpha.com/api/v3/service_plans/458/picks?include=ticker%2Cticker.sector%2Cticker.tickerMetrics%2Cticker.tickerMetrics.metricType&page[size]=100&sort=undefined'
    closed_url = 'https://seekingalpha.com/api/v3/service_plans/458/picks?include=ticker%2Cticker.sector%2Cticker.tickerMetrics%2Cticker.tickerMetrics.metricType&page[size]=100&sort=undefined&status=closed'

    current_data = fetch_data(current_url, session, headers)
    closed_data = fetch_data(closed_url, session, headers)

    if not (current_data and closed_data):
        print("未能成功获取所有数据")
        return False

    included_current = {item['id']: item for item in current_data['included']}
    included_closed = {item['id']: item for item in closed_data['included']}
    current_stock_data = process_data(current_data['data'], included_current)
    closed_stock_data = process_data(closed_data['data'], included_closed)

    columns = [
        'ID', 'Buy Price', 'Sell Price', 'Total Return', 'Price Return',
        'Created At', 'Removed At', 'Article Title', 'Ticker ID', 'Ticker Symbol', 'Company Name', 'Sector', 'Rating', 'Holding %'
    ]

    pd.DataFrame(current_stock_data, columns=columns).to_csv('current_alpha_picks.csv', index=False)
    pd.DataFrame(closed_stock_data, columns=columns).to_csv('closed_alpha_picks.csv', index=False)

    print("数据已保存到current_alpha_picks.csv和closed_alpha_picks.csv文件中")
    return True


# --------------------------------------------------------------------------
# Metric helpers
# --------------------------------------------------------------------------

def load_data_from_csv(file_path):
    """Load a CSV, trying a series of encodings."""
    encodings = ['utf-8', 'latin1', 'ISO-8859-1', 'cp1252']
    for encoding in encodings:
        try:
            return pd.read_csv(file_path, encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("Failed to read the file with specified encodings.")


def calculate_cagr(initial_price, final_price, years):
    return (final_price / initial_price) ** (1 / years) - 1


def _price_column(data):
    """Return the close-price series, tolerating yfinance API changes.

    Older yfinance exposed 'Adj Close'. From 0.2.51 onward prices are
    auto-adjusted and only 'Close' is returned, which made the previous
    `data['Adj Close']` calls fail. Recent versions also return MultiIndex
    columns even for a single ticker.
    """
    columns = data.columns
    level0 = columns.get_level_values(0) if isinstance(columns, pd.MultiIndex) else columns
    name = 'Adj Close' if 'Adj Close' in level0 else 'Close'
    series = data[name]
    if isinstance(series, pd.DataFrame):
        series = series.iloc[:, 0]
    return series


def fetch_close_prices(ticker, start_date, end_date):
    """Daily close prices for one ticker as a clean Series."""
    data = yf.download(ticker, start=start_date, end=end_date, progress=False)
    if data.empty:
        raise ValueError(f"No price data returned for {ticker}")
    return _price_column(data).dropna()


def calculate_daily_returns(prices):
    return prices.pct_change().dropna()


def calculate_sharpe_ratio(daily_returns, risk_free_rate):
    """Annualised Sharpe ratio using a consistent annual risk-free rate."""
    excess_returns = daily_returns - risk_free_rate / TRADING_DAYS
    standard_deviation = excess_returns.std()
    if not np.isfinite(standard_deviation) or standard_deviation < MIN_STD:
        return np.nan
    return excess_returns.mean() / standard_deviation * np.sqrt(TRADING_DAYS)


def calculate_weighted_cagr(file_path, our_picks):
    """Holding-weighted return of the pick portfolio.

    Note: 'Total Return' in the picks CSV is already expressed in percent, so
    the result is a percentage (matching the committed financial_metrics.csv).
    """
    data = load_data_from_csv(file_path)
    data.columns = data.columns.str.strip()
    data['Holding %'] = pd.to_numeric(data['Holding %'], errors='coerce').fillna(0)
    our_picks_data = data[data['Ticker Symbol'].str.upper().isin([t.upper() for t in our_picks])].copy()
    our_picks_data['Total Return'] = pd.to_numeric(our_picks_data['Total Return'], errors='coerce').fillna(0)
    our_picks_data['Weighted CAGR'] = our_picks_data['Total Return'] * (our_picks_data['Holding %'] / 100)
    return our_picks_data['Weighted CAGR'].sum()


def calculate_weighted_sharpe_ratio(file_path, our_picks, risk_free_rate, start_date, end_date):
    data = load_data_from_csv(file_path)
    data.columns = data.columns.str.strip()
    data['Holding %'] = pd.to_numeric(data['Holding %'], errors='coerce').fillna(0)
    our_picks_data = data[data['Ticker Symbol'].str.upper().isin([t.upper() for t in our_picks])].copy()

    weighted_sharpe_sum = 0
    for _, row in our_picks_data.iterrows():
        ticker = row['Ticker Symbol']
        holding_percent = row['Holding %']
        if holding_percent > 0:
            try:
                prices = fetch_close_prices(ticker, start_date, end_date)
                sharpe = calculate_sharpe_ratio(calculate_daily_returns(prices), risk_free_rate)
                if not np.isnan(sharpe):
                    weighted_sharpe_sum += sharpe * (holding_percent / 100)
            except Exception as e:
                print(f'Error processing {ticker}: {e}')

    return weighted_sharpe_sum


def main():
    _load_dotenv_if_available()
    email = _require_env('SEEKINGALPHA_EMAIL')
    password = _require_env('SEEKINGALPHA_PASSWORD')

    if not scrape_seeking_alpha_picks(email, password):
        raise SystemExit("Could not retrieve the pick data; aborting the backtest.")

    our_picks = [
        'NUE', 'VLO', 'ARCH', 'COP', 'AMR', 'BXC', 'SU', 'TA', 'CVX',
        'LTHM', 'MHO', 'XOM', 'HLIT', 'SMCI', 'DINO', 'MOD', 'MPC',
        'TEX', 'JXN', 'URI', 'ASC', 'PERI', 'TGLS', 'ACLS', 'CAAP', 'POWL', 'UBER',
        'CRM', 'AMPH', 'GRBK', 'STRL', 'META', 'GOOGL', 'TMUS', 'ANF', 'CLS', 'MFC',
        'APP', 'CMCSA', 'PEP', 'TWLO', 'OKTA', 'CAH', 'RCL',
        'EAT', 'GCT', 'GM', 'BLBD', 'SKYW', 'SFM', 'BRK-B'
    ]

    file_path = 'closed_alpha_picks.csv'

    today = datetime.today()
    one_year_ago = (today - timedelta(days=365)).strftime('%Y-%m-%d')
    two_years_ago = (today - timedelta(days=365 * 2)).strftime('%Y-%m-%d')
    today_str = today.strftime('%Y-%m-%d')

    # Each benchmark carries its own CAGR window; the Sharpe window is shared so
    # the ratios are directly comparable.
    benchmarks = {
        '3 Months Treasury Bills': {'ticker': 'TBIL', 'cagr_start': one_year_ago, 'years': 1},
        '1 year Treasury Bills':   {'ticker': 'SHY',  'cagr_start': one_year_ago, 'years': 1},
        '2 years Treasury Notes':  {'ticker': 'SHY',  'cagr_start': two_years_ago, 'years': 2},
        'Gold Spot Price':         {'ticker': 'GLD',  'cagr_start': one_year_ago, 'years': 1},
        'Silver Price':            {'ticker': 'SLV',  'cagr_start': one_year_ago, 'years': 1},
        'Nasdaq':                  {'ticker': '^IXIC', 'cagr_start': one_year_ago, 'years': 1},
        'S&P 500':                 {'ticker': '^GSPC', 'cagr_start': one_year_ago, 'years': 1},
    }

    # Keyed by asset name rather than relying on two separate loops appending to
    # parallel lists in matching order.
    results = {}

    results['Our Picks'] = {
        'CAGR': calculate_weighted_cagr(file_path, our_picks),
        'Sharpe Ratio': calculate_weighted_sharpe_ratio(
            file_path, our_picks, RISK_FREE_RATE, SHARPE_START, SHARPE_END),
    }

    for asset, details in benchmarks.items():
        try:
            cagr_prices = fetch_close_prices(details['ticker'], details['cagr_start'], today_str)
            cagr = calculate_cagr(cagr_prices.iloc[0], cagr_prices.iloc[-1], details['years']) * 100

            sharpe_prices = fetch_close_prices(details['ticker'], SHARPE_START, SHARPE_END)
            sharpe = calculate_sharpe_ratio(calculate_daily_returns(sharpe_prices), RISK_FREE_RATE)
        except Exception as e:
            print(f'Error processing {asset}: {e}')
            cagr, sharpe = np.nan, np.nan

        results[asset] = {'CAGR': cagr, 'Sharpe Ratio': sharpe}

    results_df = pd.DataFrame(
        [{'Asset': asset, 'CAGR': values['CAGR'], 'Sharpe Ratio': values['Sharpe Ratio']}
         for asset, values in results.items()]
    )
    results_df.to_csv('financial_metrics.csv', index=False)

    print(f"\nRisk-free rate used for all Sharpe ratios: {RISK_FREE_RATE:.2%}")
    print(results_df.to_string(index=False))
    print('\nFinancial metrics have been saved to financial_metrics.csv')


if __name__ == "__main__":
    main()