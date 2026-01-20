# audit_data.py

import os
import pandas as pd
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

def run_audit():
    print("🕵️‍♂️ RUNNING DATA HEALTH AUDIT...\n")
    conn = get_db_connection()
    
    # 1. Get all known stations (from the stations table)
    stations_df = pd.read_sql("SELECT station_name, city FROM stations", conn)
    print(f"📍 Stations in Database: {len(stations_df)}")
    
    # 2. Count AQI records per station
    aqi_query = """
    SELECT station_name, COUNT(*) as aqi_count, 
           MIN(time) as first_seen, MAX(time) as last_seen
    FROM aqi_data 
    GROUP BY station_name
    """
    aqi_stats = pd.read_sql(aqi_query, conn)
    
    # 3. Count Traffic records per station
    traffic_query = """
    SELECT station_name, COUNT(*) as traffic_count
    FROM traffic_data
    GROUP BY station_name
    """
    traffic_stats = pd.read_sql(traffic_query, conn)
    
    conn.close()
    
    # 4. Merge everything to see the gaps
    # We merge on station_name
    merged = pd.merge(stations_df, aqi_stats, on='station_name', how='outer')
    merged = pd.merge(merged, traffic_stats, on='station_name', how='outer')
    
    # Fill NaNs with 0 for easier reading
    merged['aqi_count'] = merged['aqi_count'].fillna(0).astype(int)
    merged['traffic_count'] = merged['traffic_count'].fillna(0).astype(int)
    
    # Display the Report
    print("\n📊 STATION HEALTH REPORT:")
    print("-" * 80)
    # We select columns to display
    display_df = merged[['station_name', 'aqi_count', 'traffic_count']]
    print(display_df.to_string(index=False))
    print("-" * 80)
    
    # 5. Analysis
    print("\n🚨 DIAGNOSIS:")
    
    # Check for "Zombie" Stations (Traffic but no AQI, or vice versa)
    missing_traffic = merged[(merged['aqi_count'] > 0) & (merged['traffic_count'] == 0)]
    
    if not missing_traffic.empty:
        print(f"❌ WARNING: The following stations have AQI data but NO Traffic data:")
        for name in missing_traffic['station_name']:
            print(f"   - {name}")
        print("   -> Solution: Run 'setup_traffic.py' again to harvest their coordinates.")
    else:
        print("✅ Traffic Mapping: Good. All active AQI stations are being tracked for traffic.")

    print("\n✅ SUMMARY:")
    print(f"   - Total AQI Records: {merged['aqi_count'].sum()}")
    print(f"   - Total Traffic Records: {merged['traffic_count'].sum()}")

if __name__ == "__main__":
    run_audit()