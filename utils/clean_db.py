# clean_db.py

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    return psycopg2.connect(
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASS'),
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT')
    )

def clean_database():
    print("🧹 STARTING DATABASE CLEANUP...")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Remove the "Zombie" Stations (No traffic data)
    zombie_stations = (
        'Bapuji Nagar, Bengaluru - KSPCB',
        'City Railway Station, Bengaluru - KSPCB',
        'Sanegurava Halli, Bengaluru - KSPCB',
        'Shivapura_Peenya, Bengaluru - KSPCB'
    )
    print(f"1. Removing {len(zombie_stations)} Zombie Stations...")
    query_zombies = "DELETE FROM aqi_data WHERE station_name IN %s"
    cursor.execute(query_zombies, (zombie_stations,))
    print(f"   > Deleted {cursor.rowcount} rows of orphan AQI data.")

    # 2. Remove "Ancient History" (Data before Traffic collection started)
    # Traffic collection started approx Nov 21st.
    cutoff_date = '2025-11-21 00:00:00'
    print(f"2. Trimming data before {cutoff_date}...")
    
    tables = ['weather_data', 'traffic_data', 'aqi_data']
    for table in tables:
        query_time = f"DELETE FROM {table} WHERE time < %s"
        cursor.execute(query_time, (cutoff_date,))
        print(f"   > Deleted {cursor.rowcount} old rows from {table}.")

    conn.commit()
    conn.close()
    print("\n✨ CLEANUP COMPLETE. Your database is now pristine.")

if __name__ == "__main__":
    clean_database()