# 🛡️ Aeris Engine: Setup & Pre-Caution Guide

This document outlines the critical steps to set up the Aeris Engine environment securely on both Local (Laptop) and Remote (AWS) systems.

---

## 🚨 CRITICAL SECURITY RULES
1.  **NEVER commit `.env` to GitHub.** Add it to your `.gitignore` immediately.
2.  **NEVER open Port 5432** on AWS Security Groups to `0.0.0.0/0`.
3.  **ALWAYS rotate keys** (AWS, API Tokens) if they are accidentally exposed.

---

## 1️⃣ Environment Setup (`.env`)
Create a file named `.env` in the root directory. Use the template below.

> **Note:** Ask the project lead for the actual values. Do not guess.

```ini
# --- API Keys ---
TOMTOM_API_KEY=your_tomtom_key_here
WAQI_TOKEN=your_waqi_token_here
# (Optional) OpenWeather key if used in older scripts
OPENWEATHER_API_KEY=your_openweather_key_here

# --- AWS Connection (Production) ---
AWS_SERVER_IP=13.202.xx.xx
AWS_USER=ubuntu
SSH_KEY_PATH=aeris-key.pem

# --- Database Credentials ---
DB_NAME=aeris_db
DB_USER=postgres
DB_PASS=your_strong_password_here
DB_HOST=localhost
DB_PORT=5432



2️⃣ AWS Production Setup (The "Fortress")
A. Security Groups (Firewall)

Configure your AWS EC2 Security Group with Inbound Rules strictly as follows:
Type	Port	Source	Purpose
SSH	22	My IP (Best) or 0.0.0.0/0	Remote Access
HTTP	80	0.0.0.0/0	Web Dashboard (Future)
HTTPS	443	0.0.0.0/0	Secure Web (Future)
Postgres	5432	DO NOT ADD	DANGER: Never open this.



B. Docker "Pro Mode" (Localhost Binding)

To ensure the database is invisible to the internet, modify deployment/docker-compose.aws.yaml:
YAML

  timescaledb:
    image: timescale/timescaledb:latest-pg16
    ports:
      - "127.0.0.1:5432:5432"  # <--- BINDS TO LOCALHOST ONLY



C. 24/7 Automation

Use nohup to keep the scheduler running after you disconnect:
Bash

# Start Scheduler
nohup python3 backend_scheduler/scheduler.py > scheduler.log 2>&1 &

# Check Process
ps aux | grep scheduler.py


3️⃣ Local Development Setup
A. Install Dependencies
Bash

python -m venv venv
# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt

B. Syncing Data (AWS -> Laptop)

We use sync_db.py to pull fresh production data to the local machine for testing.

    Method: SSH Tunneling (Does not require open DB ports).

    Command: python sync_db.py

    Warning: This WIPES the local database before importing.

4️⃣ Disaster Recovery

If the AWS database is compromised or deleted:

    Stop Containers: docker-compose -f deployment/docker-compose.aws.yaml down

    Delete Volume: docker volume rm ubuntu_timescaledb_prod_data

    Restart: docker-compose -f deployment/docker-compose.aws.yaml up -d

    Restore Schema: Use restore_schema.sql locally.

    Restore Stations: Update restore_to_aws.py to target ["stations"] and run it.


