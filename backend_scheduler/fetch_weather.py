# fetch_weather.py (v2.0 - Now with Database!)

import os
import requests
import json
import psycopg2
import time
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

# --- API Configuration ---
API_KEY = os.getenv('OPENWEATHER_API_KEY')
BENGALURU_LAT = 12.9716
BENGALURU_LON = 77.5946
API_URL = f"https://api.openweathermap.org/data/3.0/onecall?lat={BENGALURU_LAT}&lon={BENGALURU_LON}&units=metric&appid={API_KEY}"

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

# --- NEW: Data Insertion Function ---
def insert_weather_data(conn, weather_data):
    """Inserts the fetched weather data into the weather_data table."""
    
    current_weather = weather_data.get('current', {})
    if not current_weather:
        print("No 'current' weather data found in API response.")
        return

    # Extract data points
    # We convert the 'dt' (timestamp) from the API into a proper timezone-aware datetime
    timestamp = datetime.fromtimestamp(current_weather.get('dt'))
    temp = current_weather.get('temp')
    humidity = current_weather.get('humidity')
    wind_speed = current_weather.get('wind_speed')
    conditions = current_weather.get('weather', [{}])[0].get('description', 'N/A')

    # Define the SQL query to insert data
    insert_query = """
    INSERT INTO weather_data (time, temperature_celsius, humidity_percent, wind_speed_ms, conditions_text)
    VALUES (%s, %s, %s, %s, %s)
    ON CONFLICT (time) DO NOTHING; 
    """
    # 'ON CONFLICT DO NOTHING' prevents duplicate entries if we run the script twice
    
    data_tuple = (timestamp, temp, humidity, wind_speed, conditions)

    try:
        cursor = conn.cursor()
        cursor.execute(insert_query, data_tuple)
        conn.commit() # Commit the transaction to save the data
        cursor.close()
        print(f"✅ [DB] Successfully inserted weather data for {timestamp}")
    except Exception as e:
        print(f"Error: Failed to insert weather data. \n{e}")
        conn.rollback() # Roll back any changes if an error occurs

# --- Main script ---
def fetch_and_store_weather():
    """Main function to fetch weather data and store it in the database."""
    print("[API] Fetching current weather data for Bengaluru...")
    
    if not API_KEY:
        print("Error: OpenWeatherMap API key not found.")
        return

    conn = None
    try:
        # 1. Fetch data from API
        response = requests.get(API_URL)
        response.raise_for_status() 
        weather_data = response.json()
        print("[API] Successfully fetched data!")
        
        # 2. Connect to Database
        conn = get_db_connection()
        if not conn:
            return # Stop if database connection failed
            
        # 3. Insert Data into Database
        insert_weather_data(conn, weather_data)

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except Exception as err:
        print(f"An other error occurred: {err}")
    finally:
        # 4. Close the database connection
        if conn:
            conn.close()
            print("[DB] Database connection closed.")

if __name__ == "__main__":
    fetch_and_store_weather()