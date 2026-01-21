# 🛠️ Aeris Engine: Database Replication Guide

This guide explains how to spin up a **fresh, exact replica** of the Aeris Engine production database on any new machine (another Cloud server, a local laptop, or a developer's PC).

---

## ✅ Phase 1: Infrastructure Setup

### 1. Create the Docker Compose File
On the new machine, create a file named `docker-compose.yaml` and paste the following configuration. This is identical to the AWS production setup but uses a local volume.

```yaml
version: '3.8'

services:
  timescaledb:
    image: timescale/timescaledb:latest-pg16
    container_name: timescaledb
    restart: always

    # 🔗 Connects to your .env file automatically
    env_file:
      - .env

    environment:
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASS}
      - POSTGRES_DB=${DB_NAME}

    ports:
      # Maps container port 5432 to host port 5432
      - "5432:5432"

    # 💾 Persistent Volume (Data survives restarts)
    volumes:
      - timescaledb_data:/var/lib/postgresql/data

# Define the storage volume
volumes:
  timescaledb_data:


  2. Configure Environment Variables

Create a file named .env in the same folder and fill in your desired credentials.

# Database Configuration
DB_NAME=aeris_db
DB_USER=postgres
DB_PASS=secure_password_here


3. Start the Container

Run the following command to download the TimescaleDB image and start the server:

docker-compose up -d

📜 Phase 2: Schema Cloning (The "Brain" Transplant)

Now that the database is running, it is empty. We need to copy the Schema (table structures, hypertable rules, indexes, and functions) from the AWS Production server.
Step A: Export Schema from AWS (Run on AWS)

This command creates a lightweight "Blueprint" file containing only the structure, not the heavy data.

docker exec timescaledb pg_dump -U postgres -s -d aeris_db > aeris_schema.sql

Step B: Import Schema to New Machine (Run on New Machine)

Place the aeris_schema.sql file in the same folder as your docker-compose.yaml on the new machine.

    Copy the file inside the container:

    docker cp aeris_schema.sql timescaledb:/tmp/aeris_schema.sql

    Apply the Blueprint:

    docker exec timescaledb psql -U postgres -d aeris_db -f /tmp/aeris_schema.sql

    🔄 Phase 3: Verify the Clone

Run this command on the new machine to confirm it is an exact structural match:

docker exec timescaledb psql -U postgres -d aeris_db -c "\dt"

Expected Output: You should see your three main tables listed:

    traffic_data

    aqi_data

    weather_data

The database is now structurally identical to Production and ready to receive data via the sync script.

