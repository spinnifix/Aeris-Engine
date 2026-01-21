💻 Local Workstation Setup Guide (Windows)

This guide explains how to set up the Aeris Engine on a Windows laptop for development, training, and visualization.
1. Prerequisites

    Docker Desktop: Installed and running (Use WSL2 backend if prompted).

    Python 3.10+: Installed (Add to PATH during installation).

    Git: Installed.

2. Project Setup & Virtual Environment

Open your terminal (Command Prompt, PowerShell, or VS Code Terminal) and run:
PowerShell

# 1. Clone the repo
git clone https://github.com/spinnifix/Aeris-Engine.git
cd Aeris-Engine

# 2. Create Virtual Environment
python -m venv venv

# 3. Activate Environment (Windows)
venv\Scripts\activate

# 4. Install Dependencies
pip install -r requirements.txt

3. Configuration (.env)

Create a .env file in the root folder (Aeris-Engine). Paste this content and fill in your details:
Ini, TOML

# --- Local Database Config ---
DB_NAME=aeris_db
DB_USER=aeris_user
DB_PASS=secure_password_here

# --- AWS Connection (For Syncing) ---
AWS_SERVER_IP=YOUR_AWS_ELASTIC_IP
AWS_USER=ubuntu
SSH_KEY_PATH=./aeris-key.pem

# --- API Keys (Optional on local, but good to have) ---
WAQI_API_TOKEN=your_token
OPENWEATHER_API_KEY=your_key

4. Start Local Database (Docker)

Start the local TimescaleDB container.
PowerShell

docker-compose -f deployment/docker-compose.local.yaml up -d

    Check status: Run docker ps. You should see aeris_timescaledb running.

5. Create Database Schema (The Empty Tables)

Before you can sync data, you must create the empty tables. If you have the aeris_schema.sql file (exported from AWS), run this:
PowerShell

# 1. Copy schema file into container
docker cp aeris_schema.sql aeris_timescaledb:/tmp/aeris_schema.sql

# 2. Execute it
docker exec aeris_timescaledb psql -U aeris_user -d aeris_db -f /tmp/aeris_schema.sql

(If you don't have the schema file, check the DB_SETUP.md guide to generate it).
6. Sync Data (AWS ➔ Local)

Now, pull the latest live data from your Cloud server to your Laptop.
PowerShell

python utils/sync_db.py

    Success Message: ✅ All tables synced successfully!

    Note: Ensure your aeris-key.pem is in the root folder.

7. Train the AI Model

Retrain the LSTM Neural Network using the fresh data you just synced.
PowerShell

python ml_engine/train_model.py

    This will save a new aeris_v1.keras model file in the ml_engine folder.

8. Run the Dashboard

Launch the visualization interface.
PowerShell

streamlit run dashboard/dashboard.py

    A browser tab will automatically open (usually at http://localhost:8501) showing your Air Quality Forecast.