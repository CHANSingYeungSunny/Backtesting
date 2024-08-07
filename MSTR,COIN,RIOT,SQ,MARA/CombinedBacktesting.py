import requests
from bs4 import BeautifulSoup
import csv
import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from tqdm import tqdm
import contextlib
import io
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import warnings

warnings.filterwarnings("ignore")

def scrape_current_price(url, selector):
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        td = soup.select_one(selector)
        if td:
            return td.get_text().strip()
    return None

def scrape_market_cap(url):
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        dd = soup.select_one('body > div:nth-of-type(2) > main > div > div:nth-of-type(2) > section > div > div:nth-of-type(2) > span > div > dl:nth-of-type(2) > div:nth-of-type(2) > dd')
        if dd:
            return dd.get_text().strip()
    return None

def scrape_btc_cap(url):
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        span = soup.select_one('body > div:nth-of-type(1) > div:nth-of-type(2) > div:nth-of-type(1) > div:nth-of-type(2) > div > div:nth-of-type(1) > div:nth-of-type(4) > table > tbody > tr:nth-of-type(1) > td:nth-of-type(8) > p > span:nth-of-type(2)')
        if span:
            return span.get_text().strip().replace(',', '').replace('$', '')
    return None

def get_stock_volume(ticker_symbol):
    ticker = yf.Ticker(ticker_symbol)
    end_date = datetime.now().date()
    
    start_date = end_date - timedelta(days=1)
    data = ticker.history(start=start_date, end=end_date)
    
    if data.empty:
        start_date = end_date - timedelta(days=3)
        data = ticker.history(start=start_date, end=end_date)
    
    if not data.empty:
        return data.iloc[-1]['Volume']
    return None

def fetch_data(ticker, date):
    try:
        start_date = date
        end_date = date + timedelta(days=7)
        with contextlib.redirect_stdout(io.StringIO()):
            stock_data = yf.download(ticker, start=start_date, end=end_date, progress=False)
            btc_data = yf.download('BTC-USD', start=start_date, end=end_date, progress=False)
        stock_close = stock_data['Close'].iloc[-1] if not stock_data.empty else None
        btc_close = btc_data['Close'].iloc[-1] if not btc_data.empty else None
        return stock_close, btc_close
    except Exception:
        return None, None

def process_stock(stock_info):
    name, symbol, url, selector = stock_info
    main_url = "https://bitcointreasuries.net/"
    stock_url = f"https://bitcointreasuries.net/entities/{url}"
    btc_cap_url = "https://coinmarketcap.com/"

    current_price = scrape_current_price(main_url, selector)
    market_cap = scrape_market_cap(stock_url)
    btc_cap = scrape_btc_cap(btc_cap_url)
    stock_volume = get_stock_volume(symbol)

    market_cap_value = float(market_cap.replace(',', '').replace('$', ''))
    btc_cap_value = float(btc_cap)
    percentage = (market_cap_value / btc_cap_value) * 100

    backtesting_data = [name, symbol, current_price, market_cap, percentage, stock_volume]

    response = requests.get(stock_url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        section = soup.select_one('body > div:nth-of-type(2) > main > div > div:nth-of-type(4) > section > div > div:nth-of-type(2)')
        
        if section:
            data = []
            rows = section.find_all('tr')
            
            for row in rows:
                cols = row.find_all('td')
                cols = [col.text.strip() for col in cols]
                if len(cols) > 0:
                    data.append({
                        'Date': cols[1] if len(cols) > 0 else "",
                        'BTC Balance': cols[2] if len(cols) > 1 else ""
                    })
            
            df = pd.DataFrame(data)
            stock = yf.Ticker(symbol)
            total_shares_outstanding = stock.info['sharesOutstanding']

            result_data = {
                'Date': [],
                'BTC Balance': [],
                'BTC Ratio': [],
                'NAV Premium': [],
                'BTC per Share': []
            }

            with tqdm(total=len(df), desc=f"Processing {symbol}", ncols=100, ascii=True) as pbar:
                for index, row in df.iterrows():
                    date_str = row['Date']
                    try:
                        btc_balance = float(row['BTC Balance'].replace(',', ''))
                        date = datetime.strptime(date_str, "%b %d, %Y")
                    except ValueError:
                        pbar.update(1)
                        continue
                    
                    stock_price, btc_price = fetch_data(symbol, date)
                    
                    if stock_price and btc_price:
                        btc_per_share = btc_balance / total_shares_outstanding
                        btc_ratio = stock_price / btc_price
                        nav_value = btc_per_share * btc_price
                        nav_premium = stock_price / nav_value
                        
                        result_data['Date'].append(date)
                        result_data['BTC Balance'].append(btc_balance)
                        result_data['BTC Ratio'].append(btc_ratio)
                        result_data['NAV Premium'].append(nav_premium)
                        result_data['BTC per Share'].append(btc_per_share)
                    else:
                        pbar.update(1)
                        continue

                    pbar.update(1)

            result_df = pd.DataFrame(result_data)
            full_index = pd.date_range(start=result_df['Date'].min(), end=pd.Timestamp.today(), freq='D')
            result_df = result_df.set_index('Date').reindex(full_index).reset_index().rename(columns={'index': 'Date'})

            print(f"Forward-filling missing values for {symbol}...")
            result_df['BTC Balance'] = result_df['BTC Balance'].ffill()

            print(f"Recalculating financial metrics for {symbol}...")
            with tqdm(total=len(result_df), desc="Recalculating Metrics", ncols=100, ascii=True) as pbar:
                for index, row in result_df.iterrows():
                    if pd.notna(row['BTC Balance']) and pd.isna(row['BTC Ratio']):
                        btc_balance = row['BTC Balance']
                        date = row['Date']
                        stock_price, btc_price = fetch_data(symbol, date)
                        if stock_price and btc_price:
                            btc_per_share = btc_balance / total_shares_outstanding
                            btc_ratio = stock_price / btc_price
                            nav_value = btc_per_share * btc_price
                            nav_premium = stock_price / nav_value
                            
                            result_df.at[index, 'BTC Ratio'] = btc_ratio
                            result_df.at[index, 'NAV Premium'] = nav_premium
                            result_df.at[index, 'BTC per Share'] = btc_per_share
                    pbar.update(1)

            latest_date_with_data = result_df.dropna().iloc[-1]['Date']
            seven_days_before = latest_date_with_data - pd.Timedelta(days=7)
            thirty_days_before = latest_date_with_data - pd.Timedelta(days=30)
            ninety_days_before = latest_date_with_data - pd.Timedelta(days=90)
            
            seven_days_row = result_df[result_df['Date'] == seven_days_before]
            thirty_days_row = result_df[result_df['Date'] == thirty_days_before]
            ninety_days_row = result_df[result_df['Date'] == ninety_days_before]
            
            latest_result_data = {
                'Date': [latest_date_with_data],
                'BTC Ratio (7d) in %': [(result_df.loc[result_df['Date'] == latest_date_with_data, 'BTC Ratio'].values[0] - result_df.loc[result_df['Date'] == seven_days_before, 'BTC Ratio'].values[0]) / result_df.loc[result_df['Date'] == seven_days_before, 'BTC Ratio'].values[0] * 100 if not seven_days_row.empty else None],
                'BTC Ratio (30d) in %': [(result_df.loc[result_df['Date'] == latest_date_with_data, 'BTC Ratio'].values[0] - result_df.loc[result_df['Date'] == thirty_days_before, 'BTC Ratio'].values[0]) / result_df.loc[result_df['Date'] == thirty_days_before, 'BTC Ratio'].values[0] * 100 if not thirty_days_row.empty else None],
                'BTC Ratio (90d) in %': [(result_df.loc[result_df['Date'] == latest_date_with_data, 'BTC Ratio'].values[0] - result_df.loc[result_df['Date'] == ninety_days_before, 'BTC Ratio'].values[0]) / result_df.loc[result_df['Date'] == ninety_days_before, 'BTC Ratio'].values[0] * 100 if not ninety_days_row.empty else None],
                'NAV Premium (7d) in %': [(result_df.loc[result_df['Date'] == latest_date_with_data, 'NAV Premium'].values[0] - result_df.loc[result_df['Date'] == seven_days_before, 'NAV Premium'].values[0]) / result_df.loc[result_df['Date'] == seven_days_before, 'NAV Premium'].values[0] * 100 if not seven_days_row.empty else None],
                'NAV Premium (30d) in %': [(result_df.loc[result_df['Date'] == latest_date_with_data, 'NAV Premium'].values[0] - result_df.loc[result_df['Date'] == thirty_days_before, 'NAV Premium'].values[0]) / result_df.loc[result_df['Date'] == thirty_days_before, 'NAV Premium'].values[0] * 100 if not thirty_days_row.empty else None],
                'NAV Premium (90d) in %': [(result_df.loc[result_df['Date'] == latest_date_with_data, 'NAV Premium'].values[0] - result_df.loc[result_df['Date'] == ninety_days_before, 'NAV Premium'].values[0]) / result_df.loc[result_df['Date'] == ninety_days_before, 'NAV Premium'].values[0] * 100 if not ninety_days_row.empty else None],
                'BTC per Share (90d) in %': [(result_df.loc[result_df['Date'] == latest_date_with_data, 'BTC per Share'].values[0] - result_df.loc[result_df['Date'] == ninety_days_before, 'BTC per Share'].values[0]) / result_df.loc[result_df['Date'] == ninety_days_before, 'BTC per Share'].values[0] * 100 if not ninety_days_row.empty else None]
            }

            latest_result_df = pd.DataFrame(latest_result_data)
            
            combined_data = backtesting_data + latest_result_df.iloc[0].tolist()[1:]
            
            plot_graphs(result_df, symbol)
            
            return combined_data
    
    return None

def plot_graphs(result_df, symbol):
    def plot_graph(x, y, y_label, title, filename):
        plt.figure(figsize=(16, 10))
        plt.plot(x, y, label=y_label)
        plt.xlabel('Date')
        plt.ylabel(y_label)
        plt.title(title)
        plt.legend()
        plt.grid()
        plt.gca().xaxis.set_major_locator(mdates.DayLocator())
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.gca().xaxis.set_minor_locator(mdates.WeekdayLocator())
        plt.gcf().autofmt_xdate(rotation=45)
        plt.savefig(filename)
        plt.close()
    
    today = pd.Timestamp.today().normalize()
    start_date_7_days = today - pd.Timedelta(days=7)
    start_date_30_days = today - pd.Timedelta(days=30)
    start_date_90_days = today - pd.Timedelta(days=90)
    
    last_7_days_df = result_df[(result_df['Date'] >= start_date_7_days) & (result_df['Date'] <= today)]
    last_30_days_df = result_df[(result_df['Date'] >= start_date_30_days) & (result_df['Date'] <= today)]
    last_90_days_df = result_df[(result_df['Date'] >= start_date_90_days) & (result_df['Date'] <= today)]

    last_7_days_df = last_7_days_df.sort_values(by='Date')
    last_30_days_df = last_30_days_df.sort_values(by='Date')
    last_90_days_df = last_90_days_df.sort_values(by='Date')
    
    plot_graph(last_7_days_df['Date'], last_7_days_df['BTC Ratio'], 'BTC Ratio', f'{symbol}/BTC Ratio Over Last 7 Days', f'{symbol}_btc_ratio_last_7_days.png')
    plot_graph(last_7_days_df['Date'], last_7_days_df['NAV Premium'], 'NAV Premium', f'NAV Premium Over Last 7 Days', f'{symbol}_nav_premium_last_7_days.png')   
    
    plot_graph(last_30_days_df['Date'], last_30_days_df['BTC Ratio'], 'BTC Ratio', f'{symbol}/BTC Ratio Over Last 30 Days', f'{symbol}_btc_ratio_last_30_days.png')
    plot_graph(last_30_days_df['Date'], last_30_days_df['NAV Premium'], 'NAV Premium', f'NAV Premium Over Last 30 Days', f'{symbol}_nav_premium_last_30_days.png')

    plot_graph(last_90_days_df['Date'], last_90_days_df['BTC Ratio'], 'BTC Ratio', f'{symbol}/BTC Ratio Over Last 90 Days', f'{symbol}_btc_ratio_last_90_days.png')
    plot_graph(last_90_days_df['Date'], last_90_days_df['NAV Premium'], 'NAV Premium', f'NAV Premium Over Last 90 Days', f'{symbol}_nav_premium_last_90_days.png')
    plot_graph(last_90_days_df['Date'], last_90_days_df['BTC per Share'], 'BTC per Share', f'BTC per Share Over Last 90 Days', f'{symbol}_btc_per_share_last_90_days.png')

def main():
    stocks = [
        ("Microstrategy", "MSTR", "1", 'table tbody tr:nth-child(1) td:nth-child(7)'),
        ("Coinbase", "COIN", "coinbase", 'body > div:nth-of-type(2) > main > div:nth-of-type(3) > div:nth-of-type(1) > div:nth-of-type(1) > div:nth-of-type(1) > div > table > tbody > tr:nth-of-type(4) > td:nth-of-type(7)'),
        ("Block, Inc.", "SQ", "block", 'html > body > div:nth-of-type(2) > main > div:nth-of-type(3) > div:nth-of-type(1) > div:nth-of-type(1) > div:nth-of-type(1) > div > table > tbody > tr:nth-of-type(7) > td:nth-of-type(7)'),
        ("Marathon Digital Holdings", "MARA", "marathon", 'html > body > div:nth-of-type(2) > main > div:nth-of-type(3) > div:nth-of-type(1) > div:nth-of-type(1) > div:nth-of-type(1) > div > table > tbody > tr:nth-of-type(2) > td:nth-of-type(7)'),
        ("Riot Platforms, Inc.", "RIOT", "riot", 'body > div:nth-of-type(2) > main > div:nth-of-type(3) > div:nth-of-type(1) > div:nth-of-type(1) > div:nth-of-type(1) > div > table > tbody > tr:nth-of-type(5) > td:nth-of-type(7)')
    ]

    all_data = []

    for stock_info in stocks:
        print(f"\nProcessing {stock_info[0]} ({stock_info[1]})...")
        stock_data = process_stock(stock_info)
        if stock_data:
            all_data.append(stock_data)

    columns = ["Name", "Symbol", "Current Price", "Market Cap", "Market Cap Ratio in %", "Volume(24h)",
               "BTC Ratio (7d) in %", "BTC Ratio (30d) in %", "BTC Ratio (90d) in %",
               "NAV Premium (7d) in %", "NAV Premium (30d) in %", "NAV Premium (90d) in %", "BTC per Share (90d) in %"]
    
    combined_df = pd.DataFrame(all_data, columns=columns)
    combined_df.to_csv('combined_data.csv', index=False)
    print("\nCombined data saved to 'combined_data.csv'")

    try:
        existing_df = pd.read_csv('historical_combined_data.csv')
        updated_df = pd.concat([existing_df, combined_df], ignore_index=True)
        updated_df.to_csv('historical_combined_data.csv', index=False)
        print("New data appended to 'historical_combined_data.csv'")
    except FileNotFoundError:
        combined_df.to_csv('historical_combined_data.csv', index=False)
        print("Created new 'historical_combined_data.csv' file")

if __name__ == "__main__":
    main()
