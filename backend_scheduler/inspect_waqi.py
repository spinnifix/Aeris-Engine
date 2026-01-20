

import os
import requests
import psycopg2
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
WAQI_TOKEN = os.getenv('WAQI_TOKEN')

# 📍 UPDATED BOUNDS
BOUNDS = "12.700000,77.350000,13.250000,77.850000"

# 🛡️ FORCE LIST (Hidden Stations)
FORCE_FETCH_IDS = ["A568831", "A567850", "A567841"]

# 🗺️ MASTER MAPPING
STATION_MAP = {
    "BTM, Bangalore":                        "BTM Layout, Bengaluru - CPCB",
    "Peenya, Bangalore":                     "Peenya, Bengaluru - CPCB",
    "BWSSB Kadabesanahalli, Bengaluru":      "BWSSB Kadabesanahalli, Bengaluru - CPCB",
    "City Railway Station, Bangalore":       "City Railway Station, Bengaluru - KSPCB",
    "SaneguravaHalli, Bangalore":            "Saneguruvanahalli, Bengaluru - KSPCB",
    "Hebbal, Bengaluru":                     "Hebbal, Bengaluru - KSPCB",
    "Hombegowda Nagar, Bengaluru":           "Hombegowda Nagar, Bengaluru - KSPCB",
    "Jayanagar 5th Block, Bengaluru":        "Jayanagar 5th Block, Bengaluru - KSPCB",
    "Silk Board, Bengaluru":                 "Silk Board, Bengaluru - KSPCB",
    "Bapuji Nagar, Bengaluru":               "Bapuji Nagar, Bengaluru - KSPCB",
    "Jigani, Bengaluru":                     "Jigani, Bengaluru - KSPCB",
    "Kasturi Nagar, Bengaluru":              "Kasturi Nagar, Bengaluru - KSPCB",
    "RVCE-Mailasandra, Bengaluru":           "RVCE-Mailasandra, Bengaluru - KSPCB",
    "Shivapura_Peenya, Bengaluru":           "Peenya, Bengaluru - CPCB"
}

def get_db_connection():
    try:
        conn = psycopg2.connect(
            dbname=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASS'),
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT')
        )
        return conn
    except Exception as e:
        print(f"❌ DB Connection Failed: {e}")
        return None

def fetch_waqi_data():
    print(f"🌍 Starting Fetch Job (Bounds: {BOUNDS})...")
    
    stations_to_process = []
    found_ids = set()

    # 1. MAP SCAN
    try:
        url = f"https://api.waqi.info/map/bounds/?latlng={BOUNDS}&token={WAQI_TOKEN}"
        data = requests.get(url, timeout=15).json()
        for s in data.get('data', []):
            stations_to_process.append(s['uid'])
            found_ids.add(str(s['uid']))
        print(f"✅ Map Scan found {len(stations_to_process)} stations.")
    except Exception as e:
        print(f"⚠️ Map scan failed ({e})")

    # 2. ADD FORCE LIST
    for fid in FORCE_FETCH_IDS:
        if fid not in found_ids:
            stations_to_process.append(fid)

    clean_records = []
    print(f"🚀 Processing {len(stations_to_process)} stations...")

    for uid in stations_to_process:
        url_id = str(uid) if str(uid).startswith('A') else f"@{uid}"
        
        try:
            r = requests.get(f"https://api.waqi.info/feed/{url_id}/?token={WAQI_TOKEN}", timeout=10)
            if r.status_code != 200: continue
            data = r.json()['data']
        except:
            continue

        # Get Name & Map It
        try:
            waqi_name = data['city']['name']
            simple_name = waqi_name.replace(", India", "").replace(", Karnataka", "").strip()
            
            db_name = STATION_MAP.get(simple_name)
            if not db_name:
                for k, v in STATION_MAP.items():
                    if k.lower() in waqi_name.lower():
                        db_name = v
                        break
            
            if not db_name: continue

            # Timestamp
            try:
                ts = datetime.strptime(data['time']['s'], "%Y-%m-%d %H:%M:%S")
            except:
                ts = datetime.now()

            # Extract Pollutants
            for p, info in data.get('iaqi', {}).items():
                p_id = p.upper()
                if p_id == "PM25": p_id = "PM2.5"
                if p_id == "PM10": p_id = "PM10"
                
                if p_id in ['PM2.5', 'PM10', 'NO2', 'SO2', 'CO', 'O3', 'NH3']:
                    val = float(info['v'])
                    
                    # 🛡️ THE ZERO FILTER: Skip invalid '0' readings
                    if val > 0:
                        clean_records.append((ts, db_name, p_id, val))
            
            print(f"   ✓ Processed: {db_name}")

        except:
            continue

    return clean_records

def save_to_db(records):
    if not records:
        print("⚠️ No valid records to save.")
        return
    
    conn = get_db_connection()
    if not conn: return
    
    query = """
    INSERT INTO aqi_data (time, station_name, pollutant_id, pollutant_avg)
    VALUES (%s, %s, %s, %s)
    ON CONFLICT (time, station_name, pollutant_id) DO NOTHING;
    """
    try:
        c = conn.cursor()
        c.executemany(query, records)
        conn.commit()
        print(f"🎉 Success! Inserted {c.rowcount} records.")
        conn.close()
    except Exception as e:
        print(f"❌ DB Error: {e}")

if __name__ == "__main__":
    data = fetch_waqi_data()
    save_to_db(data)