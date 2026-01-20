# create_tables.py
import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def connect_to_db():
    """Establishes a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            dbname=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASS'),
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT')
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        print("✅ Connection to PostgreSQL database successful!")
        return conn
    except psycopg2.Error as e:
        print(f"Error: Could not connect to the database. \n{e}")
        return None

def create_tables(conn):
    """Creates the tables for storing weather and AQI data."""
    if not conn:
        return

    try:
        cursor = conn.cursor()
        
        # --- 1. Create the Weather Data Table ---
        # This will store data from OpenWeatherMap
        print("Creating 'weather_data' table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS weather_data (
                time TIMESTAMPTZ NOT NULL,
                temperature_celsius NUMERIC,
                humidity_percent NUMERIC,
                wind_speed_ms NUMERIC,
                conditions_text TEXT,
                PRIMARY KEY (time)
            );
        """)

        # --- 2. Create the AQI Data Table ---
        # This will store the raw pollutant data from CPCB
        print("Creating 'aqi_data' table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS aqi_data (
                time TIMESTAMPTZ NOT NULL,
                station_name TEXT NOT NULL,
                pollutant_id TEXT NOT NULL,
                pollutant_avg NUMERIC,
                PRIMARY KEY (time, station_name, pollutant_id)
            );
        """)

        print("✅ Tables created successfully (if they didn't exist).")

        # --- 3. Convert Tables to TimescaleDB Hypertables ---
        # This is the "magic" of TimescaleDB. It partitions the data
        # by time, making queries much faster.
        print("Converting tables to hypertables...")
        
        # We only need to do this once. The 'IF NOT EXISTS' is crucial.
        cursor.execute("SELECT create_hypertable('weather_data', 'time', if_not_exists => TRUE);")
        cursor.execute("SELECT create_hypertable('aqi_data', 'time', if_not_exists => TRUE);")

        print("✅ Hypertables configured successfully.")

        cursor.close()
    except psycopg2.Error as e:
        print(f"Error creating tables or hypertables: \n{e}")
    finally:
        if conn:
            conn.close()
            print("Database connection closed.")

if __name__ == "__main__":
    connection = connect_to_db()
    if connection:
        create_tables(connection)