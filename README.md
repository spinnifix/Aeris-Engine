# 🌍 Aeris Engine

**Aeris Engine** is a Hybrid Cloud-Edge Air Quality Forecasting System. It collects real-time traffic, weather, and AQI data on the cloud, syncs it to a local edge device, trains an LSTM neural network, and visualizes future air quality trends.

## 🏗️ Architecture

1.  **Cloud Layer (AWS):** * Dockerized TimescaleDB for high-volume time-series storage.
    * Python Scheduler running 24/7 to fetch data from 3 separate APIs.
2.  **Edge Layer (Local Machine):**
    * Machine Learning Engine (TensorFlow/Keras) for training and prediction.
    * Streamlit Dashboard for real-time visualization.
3.  **The Bridge:** * Custom synchronization script that streams raw data securely from AWS to Local DB.

## 🚀 Setup Guide

### 1. Prerequisites
* Docker Desktop installed.
* Python 3.10+
* An AWS EC2 instance (for the cloud layer).

### 2. Installation
1.  Clone the repo:
    ```bash
    git clone [https://github.com/YourUsername/Aeris-Engine.git](https://github.com/YourUsername/Aeris-Engine.git)
    cd Aeris-Engine
    ```
2.  Set up environment variables:
    * Copy `.env.example` to `.env`
    * Fill in your API keys and Database credentials.

### 3. Running the Local Database
```bash
docker-compose -f deployment/docker-compose.local.yaml up -d


This is the exact, phase-by-step roadmap to turning your project into a professional GitHub repository. We will start from scratch in a new folder to avoid messing up your currently running system.
Phase 1: The Safe House (Setup)

We will create a clean workspace and strict security rules immediately.

    Create a New Folder:

        Go to your Desktop or Documents (anywhere outside your current project folder).

        Create a new folder named: Aeris-Engine

    Create the Security File (.gitignore):

        Inside Aeris-Engine, create a file named .gitignore (no extension).

        Open it with Notepad/VS Code and paste this exactly:
        Plaintext

        # Secrets - NEVER COMMIT THESE
        .env
        *.pem
        *.ppk
        *.key
        *.json

        # Python & System Junk
        __pycache__/
        *.pyc
        venv/
        .DS_Store

        # Data & Logs (Too big or private)
        *.log
        *.csv
        *.dump
        *.sql
        timescaledb_data/

        Save and close.

Phase 2: Structural Renovation (Moving Files)

We will recreate your architecture using logical folders. Go into your Aeris-Engine folder and create these 5 sub-folders:

    deployment

    backend_scheduler

    ml_engine

    dashboard

    utils

Now, copy (do not cut) your specific files into these new homes based on this map:
📂 1. deployment/ (Infrastructure)

    Take aws_files/docker-compose.yml -> Rename it to docker-compose.aws.yaml -> Put here.

    Take Main/docker-compose.yml -> Rename it to docker-compose.local.yaml -> Put here.

📂 2. backend_scheduler/ (The AWS Brain)

    From your aws_files folder, copy these files here:

        scheduler.py

        fetch_aqi.py

        fetch_traffic.py

        fetch_weather.py

        inspect_waqi.py

        requirements.txt (The one from aws_files)

📂 3. ml_engine/ (The Intelligence)

    From your Main folder, copy these files here:

        train_model.py

        predict.py

        preprocessor.py

        verify_accuracy.py

        aeris_v1.keras

        scaler.gz

📂 4. dashboard/ (The Face)

    From your Main folder, copy:

        dashboard.py

        If you have an assets folder (images), copy that too.

📂 5. utils/ (The Tools)

    From Main, copy:

        sync_db.py (The final "Stream-to-Host" version we just made)

        setup_tables.py (if you have it)

    From tools, copy:

        audit_data.py

        clean_db.py

Phase 3: The "Works for Everyone" Fix (Abstracting Configs)

Your scripts currently have your secrets hardcoded. We need to create a template so others can use the project without stealing your keys.

    Create an Environment Template:

        In the root Aeris-Engine folder, create a file named .env.example.

        Paste this content:
        Ini, TOML

        # --- Database Configuration ---
        DB_NAME=aeris_db
        DB_USER=postgres
        DB_PASS=change_me_to_strong_password

        # --- AWS Connection (For Sync) ---
        AWS_SERVER_IP=x.x.x.x
        AWS_USER=ubuntu
        SSH_KEY_PATH=./aeris-key.pem

        # --- API Keys ---
        WAQI_API_TOKEN=get_free_token_from_waqi_info
        OPENWEATHER_API_KEY=get_free_token_from_openweather

    Update sync_db.py (One tiny change):

        Open utils/sync_db.py in your code editor.

        Look at the top where SERVER_IP is defined.

        Change it to look like this:
        Python

        # Load from environment variable, fallback to empty if missing
        SERVER_IP = os.getenv("AWS_SERVER_IP", "YOUR_AWS_IP_HERE") 

        Note: It is okay to leave your IP as a default if this is a private repo, but for a public one, replace the IP with a placeholder string.

Phase 4: The Manual (README.md)

This makes your project look professional.

    Create a file named README.md in the root folder.

    Paste this text:

Markdown

# 🌍 Aeris Engine

**Aeris Engine** is a Hybrid Cloud-Edge Air Quality Forecasting System. It collects real-time traffic, weather, and AQI data on the cloud, syncs it to a local edge device, trains an LSTM neural network, and visualizes future air quality trends.

## 🏗️ Architecture

1.  **Cloud Layer (AWS):** * Dockerized TimescaleDB for high-volume time-series storage.
    * Python Scheduler running 24/7 to fetch data from 3 separate APIs.
2.  **Edge Layer (Local Machine):**
    * Machine Learning Engine (TensorFlow/Keras) for training and prediction.
    * Streamlit Dashboard for real-time visualization.
3.  **The Bridge:** * Custom synchronization script that streams raw data securely from AWS to Local DB.

## 🚀 Setup Guide

### 1. Prerequisites
* Docker Desktop installed.
* Python 3.10+
* An AWS EC2 instance (for the cloud layer).

### 2. Installation
1.  Clone the repo:
    ```bash
    git clone [https://github.com/YourUsername/Aeris-Engine.git](https://github.com/YourUsername/Aeris-Engine.git)
    cd Aeris-Engine
    ```
2.  Set up environment variables:
    * Copy `.env.example` to `.env`
    * Fill in your API keys and Database credentials.

### 3. Running the Local Database
```bash
docker-compose -f deployment/docker-compose.local.yaml up -d

4. Syncing Data from Cloud

To pull the latest dataset from your AWS production server:
python utils/sync_db.py

5. Running the Dashboard
streamlit run dashboard/dashboard.py




