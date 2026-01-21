☁️ AWS Server Setup & 24/7 Scheduler Guide

This guide covers how to take a fresh Ubuntu EC2 instance and turn it into the production server for Aeris Engine.
1. System Preparation & Installation

Run these commands one by one on your fresh AWS EC2 instance (Ubuntu).
Bash

# 1. Update the system package list
sudo apt update && sudo apt upgrade -y

# 2. Install Docker, Docker Compose, and Python tools
sudo apt install -y docker.io docker-compose-v2 python3-pip python3-venv git

# 3. Enable Docker to start on boot
sudo systemctl enable --now docker

# 4. Add your user to the Docker group (prevents needing 'sudo' for docker commands)
sudo usermod -aG docker $USER

⚠️ Critical Step: After running step 4, disconnect and reconnect (SSH logout/login) to apply the permission changes.
2. Project Setup & Virtual Environment
Bash

# 1. Clone the repository (Replace with your repo URL)
git clone https://github.com/spinnifix/Aeris-Engine.git
cd Aeris-Engine

# 2. Create the Python Virtual Environment
python3 -m venv venv

# 3. Activate the environment
source venv/bin/activate

# 4. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

3. Configuration (.env)

You need to create the secrets file. Run this command to open a text editor:
Bash

nano .env

Paste the following content (Right-click to paste in PuTTY/Terminal), but replace the values with your real keys:
Ini, TOML

# --- Database Configuration ---
DB_NAME=aeris_db
DB_USER=postgres
DB_PASS=YOUR_STRONG_PASSWORD_HERE

# --- API Keys ---
# Get this from: https://aqicn.org/data-platform/token/
WAQI_API_TOKEN=your_waqi_token_here

# Get this from: https://home.openweathermap.org/api_keys
OPENWEATHER_API_KEY=your_openweather_key_here

# --- AWS Config (Not needed for the server itself, but good to keep) ---
AWS_SERVER_IP=127.0.0.1
AWS_USER=ubuntu
SSH_KEY_PATH=./aeris-key.pem

Press Ctrl+X, then Y, then Enter to save and exit.
4. Start the Database (Docker)

Launch the TimescaleDB container in background mode:
Bash

docker-compose -f deployment/docker-compose.aws.yaml up -d

Verify it is running with docker ps.
5. Start the Scheduler 24/7

We use nohup (No Hang Up) to keep the scheduler running even after you disconnect your SSH session.
Bash

# 1. Ensure your venv is active (if not already)
source venv/bin/activate

# 2. Start the scheduler in the background
nohup python3 backend_scheduler/scheduler.py > scheduler.log 2>&1 &

✅ You are done!

    To check if it's running: Type ps aux | grep python

    To read the logs: Type tail -f scheduler.log

    To stop it: Find the Process ID (PID) from the check command and run kill <PID>.