### **README.md for Program I**

---

# WhaleWisdom Data Fetching, Cleaning, and Backtesting Program

This Python program fetches, cleans, and backtests financial data from WhaleWisdom using its API. The program implements a basic backtesting strategy based on the z-score of the current percentage of portfolio holdings.

## Features

- Fetch financial data for multiple filer IDs from WhaleWisdom.
- Clean and save the fetched data to a CSV file.
- Implement a basic backtesting strategy using z-scores.
- Calculate key financial metrics such as Total Return, CAGR, Sharpe Ratio, and Max Drawdown.
- Visualize the results of the backtest with cumulative returns plotted against the portfolio value.

## Prerequisites

- Python 3.6+
- Required Python libraries: `requests`, `hmac`, `hashlib`, `base64`, `json`, `datetime`, `tqdm`, `pandas`, `numpy`, `matplotlib`

Install the required Python libraries using pip:

```bash
pip install requests tqdm pandas numpy matplotlib
```

## Usage

1. **Set API Keys**:
   These come from the `WHALEWISDOM_SHARED_ACCESS_KEY` and `WHALEWISDOM_SECRET_ACCESS_KEY`
   environment variables. Copy `.env.example` to `.env` (git-ignored) and fill in your own keys,
   so nothing secret is committed.

2. **Fetch Data**:
   The program fetches data for a list of known filer IDs over a specified date range. The fetched data is saved to a file named `whale_wisdom_data.json`.

3. **Clean and Save Data**:
   After fetching the data, the program cleans it by filtering out unnecessary fields and removing NaN values. The cleaned data is saved to `cleaned_holdings.csv`.

4. **Backtesting**:
   The program implements a backtesting strategy by calculating z-scores based on the current percentage of portfolio holdings. It calculates key financial metrics and plots the cumulative returns against the portfolio value.

5. **Run the Program**:
   Simply run the program by executing the following command:

   ```bash
   python program1.py
   ```

6. **Inspect Results**:
   The results of the backtesting strategy will be saved in `backtesting_results.csv` and visualized in a plot saved as `backtesting_results.png`.

## File Structure

- `program1.py`: The main program file containing all the functions and the main execution flow.
- `whale_wisdom_data.json`: File to store raw fetched data from WhaleWisdom (generated after running the program).
- `cleaned_holdings.csv`: File to store cleaned data after processing.
- `backtesting_results.csv`: File to store backtesting results.
- `backtesting_results.png`: Visualization of the backtesting strategy returns.

### **README.md for Program II**

---

# WhaleWisdom Data Fetching, Cleaning, and Z-Score Backtesting Program

This Python program is designed to fetch financial data from the WhaleWisdom API, clean and process the data, and then backtest a trading strategy using z-scores.

## Features

- Fetch data for multiple filer IDs from the WhaleWisdom API.
- Clean and save the fetched data to a CSV file.
- Implement a trading strategy based on z-scores calculated from historical price data.
- Calculate and display key financial metrics, including Total Return, CAGR, Sharpe Ratio, and Max Drawdown.
- Visualize cumulative returns against the portfolio value.

## Prerequisites

- Python 3.6+
- Required Python libraries: `requests`, `hmac`, `hashlib`, `base64`, `json`, `datetime`, `tqdm`, `pandas`, `numpy`, `matplotlib`

Install the required Python libraries using pip:

```bash
pip install requests tqdm pandas numpy matplotlib
```

## Usage

1. **Set API Keys**:
   These come from the `WHALEWISDOM_SHARED_ACCESS_KEY` and `WHALEWISDOM_SECRET_ACCESS_KEY`
   environment variables. Copy `.env.example` to `.env` (git-ignored) and fill in your own keys,
   so nothing secret is committed.

2. **Fetch Data**:
   The program fetches data for a list of filer IDs and saves the results to a file named `whale_wisdom_data.json`.

3. **Clean Data**:
   The fetched data is cleaned by removing unnecessary fields and handling missing values. The cleaned data is saved to `cleaned_holdings.csv`.

4. **Backtesting**:
   The program calculates z-scores and implements a basic trading strategy based on these z-scores. Key financial metrics are calculated, and the strategy's performance is visualized.

5. **Run the Program**:
   Simply run the program by executing the following command:

   ```bash
   python program2.py
   ```

6. **Inspect Results**:
   The backtesting results are saved in `backtesting_results2.csv`, and the visualization is saved as `backtesting_results2.png`.

## File Structure

- `program2.py`: The main program file containing all the functions and the main execution flow.
- `whale_wisdom_data.json`: File to store raw fetched data from WhaleWisdom (generated after running the program).
- `cleaned_holdings.csv`: File to store cleaned data after processing.
- `backtesting_results2.csv`: File to store backtesting results.
- `backtesting_results2.png`: Visualization of the backtesting strategy returns.
