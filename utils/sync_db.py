import subprocess
import os
import shutil
import sys
import platform
import stat
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- ⚙️ CONFIGURATION ---
SERVER_IP = os.getenv("AWS_SERVER_IP", "13.202.198.74")
REMOTE_USER = os.getenv("AWS_USER", "ubuntu")
REMOTE_CONTAINER = "timescaledb"
REMOTE_DB_USER = "postgres"

LOCAL_CONTAINER = "aeris_timescaledb"
LOCAL_DB_USER = "aeris_user"

# Get password from .env (Crucial for the fix)
DB_PASS = os.getenv("DB_PASS")

KEY_FILE = os.getenv("SSH_KEY_PATH", "aeris-key.pem")
TEMP_KEY = "temp_secure_key.pem"
TABLES = ["traffic_data", "aqi_data", "weather_data"]

def run_command(command, shell=True):
    try:
        # stdin=subprocess.DEVNULL prevents SSH from hanging waiting for input
        subprocess.check_call(command, shell=shell, stdin=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        print("❌ Error encountered. Stopping.")
        force_delete_temp_key()
        sys.exit(1)

def force_delete_temp_key():
    if os.path.exists(TEMP_KEY):
        if platform.system() == "Windows":
            icacls_cmd = r"C:\Windows\System32\icacls.exe"
            subprocess.run(f'"{icacls_cmd}" "{TEMP_KEY}" /reset', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                os.chmod(TEMP_KEY, stat.S_IWRITE)
            except:
                pass
        try:
            os.remove(TEMP_KEY)
        except Exception:
            pass

def fix_permissions_windows(file_path):
    print("   -> 🛡️  Applying Windows-specific security fix to key...")
    username = os.getenv("USERNAME")
    icacls_cmd = r"C:\Windows\System32\icacls.exe"
    subprocess.run(f'"{icacls_cmd}" "{file_path}" /reset', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    cmd = f'"{icacls_cmd}" "{file_path}" /inheritance:r /grant:r "{username}:R"'
    try:
        subprocess.check_output(cmd, shell=True)
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Warning: Could not fix permissions: {e}")

def sync():
    print("🚀 Starting Database Sync (Stream-to-Host Mode)...")
    
    if not DB_PASS:
        print("❌ Error: DB_PASS not found in .env file.")
        sys.exit(1)

    force_delete_temp_key()

    print("🔑 Preparing secure key...")
    shutil.copy(KEY_FILE, TEMP_KEY)
    if platform.system() == "Windows":
        fix_permissions_windows(TEMP_KEY)
    
    ssh_opts = f"-i {TEMP_KEY} -o StrictHostKeyChecking=no -o ServerAliveInterval=60"

    # --- STEP 1: CLEAN LOCAL DATA ---
    print(f"🧹 Clearing existing local data in '{LOCAL_CONTAINER}'...")
    truncate_cmd = (
        f"docker exec {LOCAL_CONTAINER} psql -U {LOCAL_DB_USER} -d aeris_db "
        f"-c \"TRUNCATE TABLE traffic_data, aqi_data, weather_data CASCADE;\""
    )
    subprocess.run(truncate_cmd, shell=True, stdin=subprocess.DEVNULL)

    for table in TABLES:
        local_csv = f"{table}.csv"
        remote_csv_path = f"/home/{REMOTE_USER}/{table}.csv"
        
        print(f"\n--- 🔄 Processing Table: {table} ---")

        # 1. EXPORT TO AWS HOST FILE
        print(f"   1️⃣  Streaming from DB to AWS Host file...")
        
        # FIX: We pass the password directly via -e (Clean & Simple)
        # We assume DB_PASS contains standard characters. If it has single quotes, this might need tweaking.
        remote_cmd = (
            f"echo 'COPY {table} TO STDOUT CSV' | "
            f"docker exec -i -e PGPASSWORD='{DB_PASS}' {REMOTE_CONTAINER} "
            f"psql -h localhost -U {REMOTE_DB_USER} -d aeris_db > {remote_csv_path}"
        )
        
        run_command(f'ssh {ssh_opts} {REMOTE_USER}@{SERVER_IP} "{remote_cmd}"')

        # 2. DOWNLOAD FROM AWS HOST TO LAPTOP
        print(f"   2️⃣  Downloading to laptop...")
        run_command(f"scp {ssh_opts} {REMOTE_USER}@{SERVER_IP}:{remote_csv_path} ./{local_csv}")

        # 3. IMPORT TO LOCAL CONTAINER
        print(f"   3️⃣  Injecting into local DB...")
        run_command(f"docker cp ./{local_csv} {LOCAL_CONTAINER}:/tmp/{local_csv}")
        
        import_cmd = (
            f"docker exec {LOCAL_CONTAINER} psql -U {LOCAL_DB_USER} -d aeris_db "
            f"-c \"\\COPY {table} FROM '/tmp/{local_csv}' CSV\""
        )
        try:
            subprocess.check_call(import_cmd, shell=True, stdin=subprocess.DEVNULL)
            print(f"   ✅ Success: {table} synced.")
        except subprocess.CalledProcessError:
            print(f"   ❌ Failed to import {table}.")

        # Cleanup
        if os.path.exists(local_csv):
            os.remove(local_csv)
            
        # Remote Cleanup
        run_command(f'ssh {ssh_opts} {REMOTE_USER}@{SERVER_IP} "rm {remote_csv_path}"')

    print("\n🧹 Cleaning up keys...")
    force_delete_temp_key()
    print("✅ All tables synced successfully! Check your row counts.")

if __name__ == "__main__":
    sync()