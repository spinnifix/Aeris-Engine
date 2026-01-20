# predict.py

import numpy as np
import pandas as pd
import tensorflow as tf
import joblib
import os
from dotenv import load_dotenv

# Import our data fetching logic
from preprocessor import fetch_data, preprocess_data, FEATURE_COLS, TARGET_COL

# --- Settings ---
MODEL_PATH = 'aeris_v1.keras'
SCALER_PATH = 'scaler.gz'
LOOKBACK_WINDOW = 24

def make_prediction():
    print("🔮 STARTING FORECAST ENGINE...")
    
    # 1. Load the Saved Model and Scaler
    if not os.path.exists(MODEL_PATH) or not os.path.exists(SCALER_PATH):
        print("❌ Error: Model or Scaler not found. Train the model first!")
        return

    print("1. Loading model and scaler...")
    model = tf.keras.models.load_model(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
    
    # 2. Get the Latest Data
    # We need the most recent data to predict the future
    raw_df = fetch_data()
    
    if raw_df.empty:
        print("❌ Error: Database is empty.")
        return

    # 3. Preprocess (Cleaning & Scaling)
    # We use the SAME scaler we trained with. Do NOT fit a new one.
    # We perform the same steps: Imputation, Cyclical Time, etc.
    
    # Reuse the logic from preprocessor, but we need to tweak it slightly
    # to ensure we use the loaded scaler.
    
    print("2. Preparing recent data...")
    # A. Sort and Clean
    df = raw_df.sort_values(by=['station_name', 'time'])
    df[FEATURE_COLS[:6]] = df.groupby('station_name')[FEATURE_COLS[:6]].transform(
        lambda group: group.interpolate(method='linear').ffill().bfill()
    )
    
    # B. Time Encoding
    df['hour'] = df['time'].dt.hour
    df['day_of_week'] = df['time'].dt.dayofweek
    df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
    df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
    df['day_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
    df['day_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
    
    # C. Scale
    # Important: transform() only, don't fit()
    df[FEATURE_COLS] = scaler.transform(df[FEATURE_COLS])

    # --- ADD THIS NEW LINE ---
    df = df.fillna(0) # Force-fill any remaining gaps with 0
    
    # 4. Select a specific station to predict for
    # Let's pick the first station available in the data
    target_station = df['station_name'].unique()[0]
    print(f"3. Targeting Station: {target_station}")
    
    station_data = df[df['station_name'] == target_station].copy()
    
    # Check if we have enough data (24 hours)
    if len(station_data) < LOOKBACK_WINDOW:
        print(f"❌ Not enough history for {target_station}. Need 24 hours, have {len(station_data)}.")
        return

    # 5. Extract the LAST 24 hours
    # This is our input to the model
    last_24_hours = station_data[FEATURE_COLS].values[-LOOKBACK_WINDOW:]
    
    # Reshape to (1, 24, 11) because the model expects a batch
    input_tensor = np.expand_dims(last_24_hours, axis=0)
    
    # 6. PREDICT!
    print("4. Running Neural Network...")
    scaled_prediction = model.predict(input_tensor)
    print(f"   > Raw Model Output (Scaled): {scaled_prediction[0][0]:.4f}")
    
    # 7. Inverse Scale (Convert back to Real AQI)
    # This is tricky. The scaler expects 11 columns, but we only have 1 prediction.
    # We create a "dummy" row, put our prediction in the AQI spot, and unscale it.
    
    dummy_row = np.zeros((1, len(FEATURE_COLS)))
    # Find the index of our target column ('pollutant_avg')
    target_index = FEATURE_COLS.index(TARGET_COL)
    dummy_row[0, target_index] = scaled_prediction[0][0]
    
    # Inverse transform
    unscaled_row = scaler.inverse_transform(dummy_row)
    predicted_aqi = unscaled_row[0, target_index]
    
    print("\n" + "="*40)
    print(f"🔮 FORECAST FOR: {target_station}")
    print(f"💨 PREDICTED PM2.5 (Next Hour): {predicted_aqi:.2f}")
    print("="*40)

if __name__ == "__main__":
    make_prediction()