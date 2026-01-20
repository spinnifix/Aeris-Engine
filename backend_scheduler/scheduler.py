import schedule
import time
import sys
import subprocess
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# --- 0. SETUP & ENVIRONMENT ---
# Force load the .env file to ensure we get the correct DB_PASS
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

print("🔌 Loading modules...")

# --- 1. THE BRUTE-FORCE FIX (Password Enforcement) ---
def enforce_db_password():
    """
    Executes a Docker command to FORCE the Postgres user password 
    to match the one in the local .env file.
    This runs before any data fetching to prevent 'authentication failed' errors.
    """
    db_pass = os.getenv("DB_PASS")
    if not db_pass:
        print("⚠️  WARNING: No DB_PASS found in .env. Skipping enforcement.")
        return

    print("🛡️  Enforcing DB password alignment...")
    # We use 'bash -c' to handle special characters in passwords safely if needed,
    # but the direct command is usually robust enough.
    # We remove '-t' because this runs in the background.
    command = f'docker exec timescaledb psql -U postgres -c "ALTER USER postgres WITH PASSWORD \'{db_pass}\';"'
    
    try:
        subprocess.run(command, shell=True, check=True, stdout=subprocess.DEVNULL)
        print("   ✅ Password enforced successfully.")
    except subprocess.CalledProcessError as e:
        print(f"   ❌ CRITICAL: Could not enforce password: {e}")


# --- 2. SAFE IMPORTS (The Safety Switches) ---
fetch_and_store_weather = None
inspect_waqi = None
fetch_and_store_aqi = None
fetch_and_store_traffic = None

# Weather
try:
    from fetch_weather import fetch_and_store_weather
    print("   ✅ Weather module loaded.")
except ImportError as e:
    print(f"   ❌ WARNING: Could not import fetch_weather: {e}")

# WAQI
try:
    import inspect_waqi
    print("   ✅ WAQI module loaded.")
except ImportError as e:
    print(f"   ❌ WARNING: Could not import inspect_waqi: {e}")

# Government AQI
try:
    from fetch_aqi import fetch_and_store_aqi
    print(f"   ✅ Gov AQI module loaded.")
except ImportError as e:
    print(f"   ❌ WARNING: Could not import fetch_aqi: {e}")

# Traffic
try:
    from fetch_traffic import fetch_and_store_traffic
    print(f"   ✅ Traffic module loaded.")
except ImportError as e:
    print(f"   ❌ WARNING: Could not import fetch_traffic: {e}")


# --- 3. ROBUST JOB WRAPPERS ---

def run_weather_job():
    print(f"\n--- ☁️ Running Weather job at {datetime.now()} ---")
    
    # 🛡️ STEP 1: FIX THE DB PASSWORD (Crucial Step)
    # We run this here because this is the first job of the hour (:00).
    # It ensures the DB is ready for Weather, AQI, and Traffic.
    enforce_db_password()
    
    # STEP 2: Run the actual Weather fetch
    if not fetch_and_store_weather:
        print("⚠️ SKIPPING: Weather module is missing or failed to import.")
        return

    try:
        fetch_and_store_weather()
    except Exception as e:
        print(f"❌ Error during Weather job: {e}")
    print("--- Weather job finished ---")

def run_dual_aqi_job():
    """Runs WAQI first, then Gov API. Failures in one do NOT stop the other."""
    print(f"\n--- 🌬️ Running DUAL AQI job at {datetime.now()} ---")
    
    # Phase 1: WAQI
    if inspect_waqi:
        try:
            print("   [Phase 1] Starting WAQI Fetch...")
            waqi_data = inspect_waqi.fetch_waqi_data()
            inspect_waqi.save_to_db(waqi_data)
            print("   ✅ Phase 1 Complete.")
        except Exception as e:
            print(f"   ❌ Phase 1 (WAQI) Failed: {e}")
    else:
        print("   ⚠️ Phase 1 Skipped: WAQI module missing.")

    # Phase 2: Gov API
    if fetch_and_store_aqi:
        try:
            print("   [Phase 2] Starting Government API Fetch...")
            fetch_and_store_aqi()
            print("   ✅ Phase 2 Complete.")
        except Exception as e:
            print(f"   ❌ Phase 2 (Gov) Failed: {e}")
    else:
        print("   ⚠️ Phase 2 Skipped: Gov AQI module missing.")
        
    print("--- AQI job finished ---")

def run_traffic_job():
    print(f"\n--- 🚗 Running Traffic job at {datetime.now()} ---")
    
    if not fetch_and_store_traffic:
        print("⚠️ SKIPPING: Traffic module is missing.")
        return

    try:
        fetch_and_store_traffic()
    except Exception as e:
        print(f"❌ Error during Traffic job: {e}")
    print("--- Traffic job finished ---")


# --- 4. THE IMMORTAL MAIN LOOP ---
print("\n🚀 Scheduler started. Waiting for top of the hour...")

# Schedule Jobs
# The password fix happens inside 'run_weather_job' automatically.
schedule.every().hour.at(":00").do(run_weather_job)
schedule.every().hour.at(":01").do(run_dual_aqi_job)
schedule.every().hour.at(":02").do(run_traffic_job)

# Show upcoming jobs
print(f"📅 Next run scheduled for: {schedule.next_run()}")

while True:
    try:
        schedule.run_pending()
        time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n👋 Manual Stop (Ctrl+C). Exiting scheduler safely.")
        sys.exit(0)
    
    except Exception as e:
        # If the scheduler ITSELF crashes, we catch it, print it, and restart the loop.
        print(f"\n🔥 CRITICAL SCHEDULER ERROR: {e}")
        print("🔄 Restarting loop in 5 seconds...")
        time.sleep(5)
