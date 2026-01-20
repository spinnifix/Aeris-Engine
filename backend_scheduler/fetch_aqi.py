# fetch_aqi.py (v3.1 - Fixed NumPy type error)

import os
import requests
import pandas as pd
import psycopg2
import time
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# --- API Configuration ---
API_KEY = os.getenv('DATA_GOV_API_KEY')
RESOURCE_ID = "3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69"
BASE_URL = "https://api.data.gov.in/resource/"
API_URL = f"{BASE_URL}{RESOURCE_ID}?api-key={API_KEY}&format=json&limit=2000"

# --- Database Connection Function ---
def get_db_connection():
    """Establishes and returns a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            dbname=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASS'),
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT')
        )
        print("✅ [DB] Successfully connected to the database.")
        return conn
    except Exception as e:
        print(f"Error: Could not connect to the database. \n{e}")
        return None

# --- Data Insertion Function (WITH FIX) ---
def insert_aqi_data(conn, aqi_records_df):
    """Inserts the fetched AQI data into the aqi_data table."""
    
    if aqi_records_df.empty:
        print("[DB] No data to insert.")
        return
    #OLD QUERY (DO NOTHING on conflict)
    # insert_query = """
    # INSERT INTO aqi_data (time, station_name, pollutant_id, pollutant_avg)
    # VALUES (%s, %s, %s, %s)
    # ON CONFLICT (time, station_name, pollutant_id) DO NOTHING;
    # """

    # OLD (Delete this):
    # ON CONFLICT (time, station_name, pollutant_id) DO NOTHING;

    # NEW (Use this):
    insert_query = """
    INSERT INTO aqi_data (time, station_name, pollutant_id, pollutant_avg)
    VALUES (%s, %s, %s, %s)
    ON CONFLICT (time, station_name, pollutant_id) 
    DO UPDATE SET 
        pollutant_avg = EXCLUDED.pollutant_avg;
    """
    
    cursor = conn.cursor()
    inserted_count = 0
    
    try:
        for index, row in aqi_records_df.iterrows():
            try:
                timestamp = datetime.strptime(row['last_update'], '%d-%m-%Y %H:%M:%S')
            except ValueError as ve:
                print(f"Warning: Skipping row with invalid date format: {row['last_update']} - {ve}")
                continue

            # --- START OF FIX ---
            
            # 1. Convert to a numpy numeric type
            pollutant_avg_np = pd.to_numeric(row['avg_value'], errors='coerce')
            
            # 2. Prepare a standard Python variable (default to None)
            pollutant_avg_py = None
            
            # 3. If the numpy value is valid (not NA/NaN)...
            if not pd.isna(pollutant_avg_np):
                # 4. ...convert it to a standard Python float.
                pollutant_avg_py = float(pollutant_avg_np)
                
            # --- END OF FIX ---

            data_tuple = (
                timestamp,
                row['station'],
                row['pollutant_id'],
                pollutant_avg_py  # Use the converted Python float or None
            )
            
            cursor.execute(insert_query, data_tuple)
            inserted_count += cursor.rowcount 

        conn.commit() 
        print(f"✅ [DB] Successfully inserted/updated {inserted_count} AQI records.")
        
    except Exception as e:
        print(f"Error: Failed to insert AQI data. \n{e}")
        conn.rollback()
    finally:
        cursor.close()

# --- Main script ---
def fetch_and_store_aqi():
    """Main function to fetch AQI data and store it in the database."""
    print("[API] Fetching Air Quality Index data...")

    if not API_KEY:
        print("Error: data.gov.in API key not found.")
        return

    conn = None
    try:
        response = requests.get(API_URL)
        response.raise_for_status()
        data = response.json()
        print("[API] Successfully fetched nationwide data!")

        records = data.get('records', [])
        if not records:
            print("[API] No records found in the API response.")
            return

        df = pd.DataFrame(records)
        
        bengaluru_df = df[df['city'].str.strip() == 'Bengaluru'].copy()

        if bengaluru_df.empty:
            print("[API] Could not find any monitoring stations for Bengaluru in the data.")
        
        conn = get_db_connection()
        if not conn:
            return
            
        insert_aqi_data(conn, bengaluru_df)

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except Exception as err:
        print(f"An other error occurred: {err}")
    finally:
        if conn:
            conn.close()
            print("[DB] Database connection closed.")

if __name__ == "__main__":
    fetch_and_store_aqi()