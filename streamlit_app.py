import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import streamlit as st
import hashlib

# Utility function to hash passwords
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Format: username: hashed_password
USER_CREDENTIALS = {
    "admin": hash_password("admin123"),
    "user1": hash_password("secret1"),
}

# Check login status
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

def login():
    st.title("🔐 Secure Access")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username in USER_CREDENTIALS and USER_CREDENTIALS[username] == hash_password(password):
            st.session_state.authenticated = True
            st.session_state.username = username
            st.rerun()
        else:
            st.error("❌ Invalid username or password")

# Require login before running the app
if not st.session_state.authenticated:
    login()
    st.stop()

# Function for SMA respect analysis (from code 1)
def get_sma(stock_data, period):
    return stock_data['Close'].rolling(window=period).mean()

def check_continuous_respect_sma(stock_data, sma_list=[34, 50, 55, 89, 100, 144, 200, 233], candle_timeframe='1d'):
    respected_smas = []

    for period in sma_list:
        sma = get_sma(stock_data, period)
        respected_continuously = True
        touch_count = 0

        for i in range(1, len(stock_data)):
            candle = stock_data.iloc[i]
            current_sma = sma.iloc[i]

            if candle['Open'] < current_sma and candle['High'] < current_sma and candle['Low'] < current_sma and candle['Close'] < current_sma:
                respected_continuously = False
                break

        if respected_continuously:
            for i in range(1, len(stock_data)):
                candle = stock_data.iloc[i]
                current_sma = sma.iloc[i]

                if candle['Low'] < current_sma and candle['High'] > current_sma:
                    touch_count += 1

            if touch_count > 0:
                respected_smas.append((period, touch_count))
            else:
                respected_smas.append((period, 0))  

    return respected_smas

# Function for NSE holidays and future dates calculation (from code 2)
nse_holidays = [
    "22-01-2024", "26-01-2024", "08-03-2024", "25-03-2024", "29-03-2024", "11-04-2024",
    "17-04-2024", "01-05-2024", "20-05-2024", "17-06-2024", "17-07-2024", "15-08-2024",
    "02-10-2024", "01-11-2024", "15-11-2024", "25-12-2024",
]

nse_holidays = [datetime.strptime(date, "%d-%m-%Y") for date in nse_holidays]

def is_trading_holiday(date):
    if date.weekday() in [5, 6]:  # Saturday or Sunday
        return True
    if date in nse_holidays:
        return True
    return False

def calculate_future_dates(start_date, cycle=1):
    degrees = [30, 45, 60, 72, 90, 120, 135, 150, 180, 210, 225, 240, 270, 300, 315, 330, 360]
    factor = 1.0146
    future_dates = {}

    if cycle == 1:
        for degree in degrees:
            days_to_add = degree * factor
            future_date = start_date + timedelta(days=days_to_add)
            
            while is_trading_holiday(future_date):
                future_date += timedelta(days=1)
            
            future_dates[degree] = future_date 
        
        if 360 not in future_dates:
            raise ValueError("360-degree date from the first cycle is not available.")
        return future_dates 

    if cycle == 2:
        last_360_degree_date = start_date  
        
        for degree in degrees:
            days_to_add = degree * factor
            future_date = last_360_degree_date + timedelta(days=days_to_add)
            
            while is_trading_holiday(future_date):
                future_date += timedelta(days=1)
            
            future_dates[f"Degree_{degree}_Second_Cycle_Date"] = future_date

    return future_dates

# Streamlit UI for stock SMA analysis and script degree filter
def main():
    st.title("Stock Analysis and Future Date Calculation")

    # Tab 1 - Stock Analysis (SMA)
    st.header("Stock SMA Respect Analysis")
    stock_symbols_input = st.text_input("Enter stock symbols (comma-separated, e.g., 'AAPL, MSFT')", "AAPL, MSFT")
    stock_symbols = stock_symbols_input.split(",") 
    stock_symbols = [symbol.strip() for symbol in stock_symbols]

    start_date = st.date_input("Start date", datetime(2024, 1, 1))
    end_date = st.date_input("End date", datetime.today())
    candle_timeframe = st.selectbox("Select candle time frame", ['1d', '1wk', '1mo'])

    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")

    extended_start_date = start_date - timedelta(days=365)
    extended_start_date_str = extended_start_date.strftime("%Y-%m-%d")

    if st.button("Analyze Stocks"):
        all_stock_results = []
        for stock_symbol in stock_symbols:
            st.write(f"\nAnalyzing {stock_symbol}...")

            stock_data = yf.download(stock_symbol, start=extended_start_date_str, end=end_date_str, interval=candle_timeframe)

            respected_smas = check_continuous_respect_sma(stock_data, candle_timeframe=candle_timeframe)

            for sma, count in respected_smas:
                all_stock_results.append({
                    "Stock Symbol": stock_symbol,
                    "Respected SMA": sma,
                    "Touch Count": count
                })

        if all_stock_results:
            df_results = pd.DataFrame(all_stock_results)
            st.dataframe(df_results)  
        else:
            st.write("No SMAs respected continuously for the selected stocks.")

    # Tab 2 - NSE Script Future Date Calculation
    st.header("NSE Script Future Date Calculation")
    df = pd.read_excel('SWING HIGH.xlsx')  # Assuming the file exists in the working directory
    df['Date'] = pd.to_datetime(df['Date'], format='%Y-%m-%d %H:%M:%S')

    date_to_scripts = {}

    for index, row in df.iterrows():
        start_date = row['Date']
        future_dates = calculate_future_dates(start_date, cycle=1)
        
        for degree, date in future_dates.items():
            if isinstance(degree, int) and degree <= 360:
                date_str = date.strftime("%d-%m-%Y")
                df.loc[index, f'Degree_{degree}_Date'] = date_str
                
                if date_str not in date_to_scripts:
                    date_to_scripts[date_str] = []
                date_to_scripts[date_str].append((row['Script'], degree))

        last_360_degree_date = future_dates.get(360)
        
        if last_360_degree_date:
            future_dates_second_cycle = calculate_future_dates(last_360_degree_date, cycle=2)
            for degree, date in future_dates_second_cycle.items():
                if isinstance(degree, str) and degree.startswith("Degree_"):
                    degree_in_second_cycle = degree
                    date_str = date.strftime("%d-%m-%Y")
                    df.loc[index, degree_in_second_cycle] = date_str
                    
                    if date_str not in date_to_scripts:
                        date_to_scripts[date_str] = []
                    date_to_scripts[date_str].append((row['Script'], degree_in_second_cycle))

    df.to_excel('updated_file_with_two_cycles.xlsx', index=False)

    filter_choice = st.radio("Do you want to filter by:", ["Date", "Script"])

    if filter_choice == "Date":
        query_date = st.text_input("Enter the date (dd-mm-yyyy):")
        if query_date:
            try:
                query_date_obj = datetime.strptime(query_date, "%d-%m-%Y")
                scripts_and_degrees = get_scripts_for_date(query_date_obj)
                if scripts_and_degrees:
                    st.write(f"Scripts and degrees on {query_date_obj.strftime('%d-%m-%Y')}:")
                    for script, degree in scripts_and_degrees:
                        st.write(f"Script: {script}, Degree: {degree}")
                else:
                    st.write(f"No scripts found for {query_date_obj.strftime('%d-%m-%Y')}.")
            except ValueError:
                st.write("Invalid date format. Please use dd-mm-yyyy.")
    elif filter_choice == "Script":
        script_input = st.text_input("Enter the script name:")
        if script_input:
            script_degrees = []
            for date_str, scripts_degrees in date_to_scripts.items():
                for script, degree in scripts_degrees:
                    if script.lower() == script_input.lower():
                        script_degrees.append((date_str, degree))

            if script_degrees:
                st.write(f"Dates and degrees for script '{script_input}':")
                for date_str, degree in script_degrees:
                    st.write(f"Date: {date_str}, Degree: {degree}")
            else:
                st.write(f"No data found for script '{script_input}'.")

def get_scripts_for_date(query_date):
    query_date_str = query_date.strftime("%d-%m-%Y")
    if query_date_str in date_to_scripts:
        return date_to_scripts[query_date_str]
    else:
        return []

if __name__ == "__main__":
    main()
