# preprocessor.py

import os
import pandas as pd
import numpy as np
import psycopg2
from dotenv import load_dotenv
from sklearn.preprocessing import MinMaxScaler

# Load environment variables
load_dotenv()

# --- Configuration ---
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')

# --- Settings ---
# How many past hours the model sees to predict the future
LOOKBACK_WINDOW = 24 
# Feature columns we want to use
FEATURE_COLS = [
    'temperature_celsius', 'humidity_percent', 'wind_speed_ms', # Weather
    'current_speed', 'congestion_factor',                       # Traffic
    'pollutant_avg',                                            # AQI (Target)
    'hour_sin', 'hour_cos', 'day_sin', 'day_cos'                # Time Time
]
TARGET_COL = 'pollutant_avg'

def get_db_connection():
    return psycopg2.connect(
        dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT
    )

def fetch_data():
    """
    Fetches data from all 3 tables and merges them into one Master DataFrame.
    NOW WITH FILTER: Only fetches the last 14 days to avoid old trial data.
    """
    print("1. [Extract] Fetching raw data from database (Last 14 Days)...")
    conn = get_db_connection()
    
    # Define the time window (e.g., last 14 days)
    time_filter = "WHERE time > NOW() - INTERVAL '30 DAYS'"
    
    # 1. Fetch Weather
    weather_query = f"SELECT time, temperature_celsius, humidity_percent, wind_speed_ms FROM weather_data {time_filter}"
    weather_df = pd.read_sql(weather_query, conn)
    weather_df['time'] = pd.to_datetime(weather_df['time']).dt.floor('H')
    weather_df = weather_df.drop_duplicates(subset=['time']).set_index('time')

    # 2. Fetch Traffic
    traffic_query = f"SELECT time, station_name, current_speed, congestion_factor FROM traffic_data {time_filter}"
    traffic_df = pd.read_sql(traffic_query, conn)
    traffic_df['time'] = pd.to_datetime(traffic_df['time']).dt.floor('H')
    
    # 3. Fetch AQI
    aqi_query = f"""
        SELECT time, station_name, pollutant_avg 
        FROM aqi_data 
        {time_filter} AND pollutant_id = 'PM2.5'
    """
    aqi_df = pd.read_sql(aqi_query, conn)
    aqi_df['time'] = pd.to_datetime(aqi_df['time']).dt.floor('H')

    conn.close()

    # --- MERGE ---
    # (Rest of the code remains exactly the same...)
    merged_df = pd.merge(aqi_df, traffic_df, on=['time', 'station_name'], how='inner')
    master_df = pd.merge(merged_df, weather_df, on='time', how='inner')
    
    print(f"   > Merged Data Shape: {master_df.shape}")
    return master_df

def preprocess_data(df):
    """
    Cleans, encodes time, and scales the data.
    """
    print("2. [Transform] Cleaning and Feature Engineering...")
    
    # A. Sort by Station and Time
    df = df.sort_values(by=['station_name', 'time'])
    
    # B. Imputation (Fill missing values)
    # We interpolate strictly within each station's data group
    df[FEATURE_COLS[:6]] = df.groupby('station_name')[FEATURE_COLS[:6]].transform(
        lambda group: group.interpolate(method='linear').ffill().bfill()
    )
    
    # C. Time Encoding (Cyclical Features)
    df['hour'] = df['time'].dt.hour
    df['day_of_week'] = df['time'].dt.dayofweek
    
    # Sine/Cosine encoding
    df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
    df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
    df['day_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
    df['day_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
    
    # D. Scaling (0 to 1)
    # We will fit the scaler now. In a real app, you save this scaler to a file to use later.
    scaler = MinMaxScaler()
    df[FEATURE_COLS] = scaler.fit_transform(df[FEATURE_COLS])
    
    print("   > Data Scaled and Encoded.")
    return df, scaler

def create_sequences(df):
    """
    Creates sliding windows for LSTM.
    Input: (Samples, 24, Features) -> Output: (Samples, 1)
    """
    print("3. [Sequence] Creating LSTM Windows...")
    
    X_sequences = []
    y_targets = []
    
    # We process each station separately so we don't mix data from Station A and Station B
    stations = df['station_name'].unique()
    
    for station in stations:
        station_data = df[df['station_name'] == station].copy()
        
        # If station has less data than the window size, skip it
        if len(station_data) < LOOKBACK_WINDOW:
            continue
            
        data_values = station_data[FEATURE_COLS].values
        target_values = station_data[TARGET_COL].values
        
        # Sliding Window Loop
        for i in range(len(data_values) - LOOKBACK_WINDOW):
            # Input: Past 24 hours
            X_sequences.append(data_values[i : i + LOOKBACK_WINDOW])
            # Output: The NEXT hour's pollution level
            y_targets.append(target_values[i + LOOKBACK_WINDOW])
            
    return np.array(X_sequences), np.array(y_targets)

if __name__ == "__main__":
    # 1. Get Raw Data
    raw_df = fetch_data()
    
    if raw_df.empty:
        print("❌ Error: Not enough intersecting data found. Keep collecting data!")
    else:
        # 2. Preprocess
        clean_df, scaler = preprocess_data(raw_df)
        
        # 3. Sequence
        X, y = create_sequences(clean_df)
        
        print(f"\n✅ PROCESSING COMPLETE")
        print(f"Original Rows: {len(raw_df)}")
        print(f"LSTM Training Examples Created: {len(X)}")
        
        if len(X) > 0:
            print(f"Input Shape (X): {X.shape}  -> (Samples, Timesteps, Features)")
            print(f"Target Shape (y): {y.shape}  -> (Samples, Target)")
            print("\nSample Input (First Window):\n", X[0])
            print("\nSample Target (First Prediction):\n", y[0])
        else:
            print("⚠️ No sequences created yet. You need at least 25 hours of continuous data.")