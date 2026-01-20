import os
import requests
import psycopg2
import time
from dotenv import load_dotenv
from datetime import datetime

# 🛡️ BULLETPROOF ENV LOADING
# This forces Python to look in the same folder as the script for .env
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, '.env')
load_dotenv(env_path)

# --- Configuration ---
TOMTOM_API_KEY = os.getenv('TOMTOM_API_KEY')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')

# --- Database Connection ---
def get_db_connection():
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT
        )
        return conn
    except Exception as e:
        print(f"❌ Error: Could not connect to the database. \n{e}")
        return None

# --- Ensure Stations Table Exists (Safety Check) ---
def ensure_stations_table(conn):
    """Creates the stations table if it doesn't exist to prevent crashes."""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stations (
            id SERIAL PRIMARY KEY,
            station_name VARCHAR(100) UNIQUE,
            latitude FLOAT,
            longitude FLOAT
        );
    """)
    # Seed with some default Bengaluru stations if empty
    cursor.execute("SELECT COUNT(*) FROM stations;")
    if cursor.fetchone()[0] == 0:
        print("⚠️ Stations table empty. Seeding default stations...")
        default_stations = [
            ("Silk Board", 12.917, 77.623),
            ("Hebbal", 13.035, 77.597),
            ("Peenya", 13.032, 77.513),
            ("MG Road", 12.975, 77.606),
            ("Whitefield", 12.969, 77.749)
        ]
        cursor.executemany(
            "INSERT INTO stations (station_name, latitude, longitude) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING;",
            default_stations
        )
    conn.commit()
    cursor.close()

# --- Fetch Stations from DB ---
def get_stations(conn):
    ensure_stations_table(conn) # Ensure table exists before reading
    cursor = conn.cursor()
    cursor.execute("SELECT station_name, latitude, longitude FROM stations;")
    stations = cursor.fetchall()
    cursor.close()
    return stations

# --- Fetch Traffic from TomTom ---
def get_traffic_data(lat, lon):
    base_url = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"
    url = f"{base_url}?key={TOMTOM_API_KEY}&point={lat},{lon}"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 429:
            print("⏳ Rate limit exceeded! Waiting...")
            time.sleep(2)
            return None
            
        if response.status_code != 200:
            return None

        data = response.json()
        flow_data = data.get('flowSegmentData', {})
        
        current_speed = flow_data.get('currentSpeed')
        free_flow_speed = flow_data.get('freeFlowSpeed')
        
        if current_speed and free_flow_speed and current_speed > 0:
            congestion_factor = free_flow_speed / current_speed
        else:
            congestion_factor = 0.0
            
        return current_speed, free_flow_speed, congestion_factor

    except Exception as e:
        print(f"⚠️ Error fetching traffic for {lat},{lon}: {e}")
        return None

# --- Main Function ---
def fetch_and_store_traffic():
    print("[Traffic] Starting traffic data collection...")
    
    if not TOMTOM_API_KEY:
        print("❌ Error: TomTom API Key not found. Check .env file.")
        return

    conn = get_db_connection()
    if not conn: return

    try:
        stations = get_stations(conn)
        print(f"[Traffic] Found {len(stations)} stations to check.")
        
        cursor = conn.cursor()
        
        # Ensure traffic_data table exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS traffic_data (
                time TIMESTAMP,
                station_name VARCHAR(100),
                current_speed FLOAT,
                free_flow_speed FLOAT,
                congestion_factor FLOAT,
                UNIQUE(time, station_name)
            );
        """)
        
        insert_query = """
            INSERT INTO traffic_data (time, station_name, current_speed, free_flow_speed, congestion_factor)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (time, station_name) DO NOTHING;
        """
        
        timestamp = datetime.now()
        records_inserted = 0

        for station_name, lat, lon in stations:
            result = get_traffic_data(lat, lon)
            
            if result:
                current_speed, free_flow_speed, congestion_factor = result
                
                cursor.execute(insert_query, (
                    timestamp, station_name, current_speed, free_flow_speed, congestion_factor
                ))
                records_inserted += 1
                time.sleep(0.5) 
        
        conn.commit()
        print(f"✅ [Traffic] Successfully stored data for {records_inserted} stations.")

    except Exception as e:
        print(f"❌ Error in traffic job: {e}")
        conn.rollback()
    finally:
        conn.close()
        print("[Traffic] Database connection closed.")

if __name__ == "__main__":
    fetch_and_store_traffic()
