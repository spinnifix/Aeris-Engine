# verify_accuracy.py
import pandas as pd
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def check_scorecard():
    try:
        conn = psycopg2.connect(
            dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASS'), host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT')
        )
        
        # This query joins your predictions with the actual future reality
        # It only shows rows where BOTH exist.
        query = """
        SELECT 
            f.station_name,
            f.target_hour,
            ROUND(f.predicted_aqi::numeric, 2) as "AI Prediction",
            a.pollutant_avg as "Actual Reality",
            ROUND((f.predicted_aqi - a.pollutant_avg)::numeric, 2) as "Error (Diff)"
        FROM forecast_logs f
        JOIN aqi_data a 
          ON f.station_name = a.station_name 
          AND f.target_hour = a.time
        WHERE a.pollutant_id = 'PM2.5'
        ORDER BY f.target_hour DESC;
        """
        
        df = pd.read_sql(query, conn)
        
        if df.empty:
            print("📭 No verified matches found yet.")
            print("   (Either you haven't made predictions, or the 'Actual' data hasn't arrived yet).")
        else:
            print(f"\n📊 ACCURACY REPORT ({len(df)} Records Verified)")
            print("="*80)
            print(df.head(15).to_string(index=False)) # Show top 15
            print("="*80)
            
            # Summary Stats
            mae = df['Error (Diff)'].abs().mean()
            print(f"\n🎯 Average Error: +/- {mae:.2f} AQI Points")
            
            if mae < 15:
                print("✅ Verdict: Excellent Accuracy")
            elif mae < 25:
                print("⚠️ Verdict: Moderate Accuracy")
            else:
                print("❌ Verdict: Needs Retraining")

        conn.close()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_scorecard()