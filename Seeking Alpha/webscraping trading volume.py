import yfinance as yf
import pandas as pd

def calculate_average_volumes(ticker):
    try:
        # Fetch historical data
        stock = yf.Ticker(ticker)
        hist = stock.history(period="6mo")  # Fetch 6 months of data for a better 3-month calculation

        # Calculate last day trading volume
        last_day_volume = hist['Volume'].iloc[-1]

        # Calculate 10-day average trading volume
        avg_10_day_volume = hist['Volume'].tail(10).mean()

        # Calculate 30-day average trading volume
        avg_30_day_volume = hist['Volume'].tail(30).mean()

        # Calculate 3-month average trading volume (approximately 65 trading days)
        avg_3_month_volume = hist['Volume'].tail(65).mean()

        return {
            "Ticker": ticker,
            "Last Day Volume": last_day_volume,
            "10-Day Avg Volume": avg_10_day_volume,
            "30-Day Avg Volume": avg_30_day_volume,
            "3-Month Avg Volume": avg_3_month_volume
        }
    except Exception as e:
        print(f"Error fetching data for {ticker}: {e}")
        return None

# List of tickers
tickers = [
    'NUE', 'VLO', 'ARCH', 'COP', 'AMR', 'BXC', 'SU', 'TA', 'CVX',
    'LTHM.CN', 'MHO', 'XOM', 'HLIT', 'SMCI', 'DINO', 'MOD', 'MPC',
    'TEX', 'JXN', 'URI', 'ASC', 'PERI', 'TGLS', 'ACLS', 'CAAP', 'POWL', 'UBER',
    'CRM', 'AMPH', 'GRBK', 'STRL', 'META', 'GOOGL', 'TMUS', 'ANF', 'CLS', 'MFC',
    'APP', 'CMCSA', 'MHO', 'MOD', 'PEP', 'TWLO', 'OKTA', 'CAH', 'RCL', 'SMCI',
    'EAT', 'GCT', 'GM', 'BLBD', 'SKYW', 'SFM', 'BRK-B'
]

# List to store results
results = []

# Calculate average volumes for each ticker
for ticker in tickers:
    volumes = calculate_average_volumes(ticker)
    if volumes:
        results.append(volumes)

# Convert results to DataFrame
df = pd.DataFrame(results)

# Save DataFrame to CSV
df.to_csv('average_volumes.csv', index=False)

print("Data saved to average_volumes.csv")
