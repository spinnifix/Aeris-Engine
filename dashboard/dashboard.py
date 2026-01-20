# dashboard.py (v5.0 - Demo Ready)

import streamlit as st
import pandas as pd
import numpy as np
import psycopg2
import os
import tensorflow as tf
import joblib
import plotly.express as px
import plotly.graph_objects as go
from datetime import timedelta
from dotenv import load_dotenv
from streamlit_autorefresh import st_autorefresh  # pip install streamlit-autorefresh

# Import Logic
from preprocessor import fetch_data, FEATURE_COLS, TARGET_COL
from virtual_sensor import generate_virtual_input

load_dotenv()

# --- Config ---
MODEL_PATH = 'aeris_v1.keras'
SCALER_PATH = 'scaler.gz'
LOOKBACK_WINDOW = 24

st.set_page_config(
    page_title="Aeris Engine | Command Center",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed" # Collapsed for full screen impact
)

# --- 1. The "Heartbeat" (Auto-Refresh) ---
# Refreshes every 60 seconds to fetch new API data
count = st_autorefresh(interval=60000, key="data_refresh")

# --- CSS Polish (Dark Mode Optimization) ---
st.markdown("""
    <style>
        .block-container {padding-top: 1rem;}
        div[data-testid="stMetricValue"] {font-size: 2.4rem !important; font-weight: 700;}
        h1 {font-size: 2.5rem !important;}
        .stAlert {border-radius: 10px;}
    </style>
""", unsafe_allow_html=True)

# --- Helpers ---
def get_db_connection():
    try:
        return psycopg2.connect(
            dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASS'), host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT')
        )
    except: return None

@st.cache_resource
def load_ai_model():
    if os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH):
        return tf.keras.models.load_model(MODEL_PATH), joblib.load(SCALER_PATH)
    return None, None

def load_stations_with_status():
    """Fetches stations AND their latest AQI for the map color coding"""
    conn = get_db_connection()
    if not conn: return pd.DataFrame()
    
    # Advanced Query: Get Station info + Latest AQI
    query = """
    SELECT s.station_name, s.latitude as lat, s.longitude as lon, 
           (SELECT pollutant_avg FROM aqi_data a 
            WHERE a.station_name = s.station_name 
            AND pollutant_id = 'PM2.5' 
            ORDER BY time DESC LIMIT 1) as latest_aqi
    FROM stations s;
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df

@st.cache_data
def load_wards():
    try:
        df = pd.read_csv('bangalore_wards_cleaned.csv')
        return df.rename(columns={'latitude': 'lat', 'longitude': 'lon'})
    except:
        return pd.DataFrame()

def get_detailed_metrics(station_name):
    """Fetches Current AQI, Previous AQI (for Delta), and Traffic"""
    conn = get_db_connection()
    metrics = {"current": None, "prev": None, "traffic": None, "history": pd.DataFrame()}
    
    if conn:
        # 1. Get last 2 AQI records for Delta
        df_aqi = pd.read_sql("""
            SELECT pollutant_avg, time FROM aqi_data 
            WHERE station_name = %s AND pollutant_id = 'PM2.5' 
            ORDER BY time DESC LIMIT 2
        """, conn, params=(station_name,))
        
        if not df_aqi.empty:
            metrics["current"] = df_aqi.iloc[0]['pollutant_avg']
            if len(df_aqi) > 1:
                metrics["prev"] = df_aqi.iloc[1]['pollutant_avg']
        
        # 2. Get Traffic
        df_trf = pd.read_sql("SELECT current_speed FROM traffic_data WHERE station_name = %s ORDER BY time DESC LIMIT 1", conn, params=(station_name,))
        if not df_trf.empty: metrics["traffic"] = df_trf.iloc[0]['current_speed']
        
        # 3. Get 24h History for Graph
        query_hist = """
            SELECT time, pollutant_avg FROM aqi_data 
            WHERE station_name = %s AND pollutant_id = 'PM2.5' 
            ORDER BY time DESC LIMIT 24
        """
        metrics["history"] = pd.read_sql(query_hist, conn, params=(station_name,)).sort_values('time')
        
        conn.close()
    return metrics

def run_prediction(target_station, model, scaler):
    # (Same logic as before, just compact)
    raw_df = fetch_data()
    if raw_df.empty: return None
    station_data = raw_df[raw_df['station_name'] == target_station].copy()
    if len(station_data) < LOOKBACK_WINDOW: return None
    
    station_data = station_data.sort_values(by='time')
    station_data[FEATURE_COLS[:6]] = station_data[FEATURE_COLS[:6]].interpolate(method='linear').ffill().bfill()
    
    # Feature Engineering
    station_data['hour'] = station_data['time'].dt.hour
    station_data['day_of_week'] = station_data['time'].dt.dayofweek
    station_data['hour_sin'] = np.sin(2 * np.pi * station_data['hour'] / 24)
    station_data['hour_cos'] = np.cos(2 * np.pi * station_data['hour'] / 24)
    station_data['day_sin'] = np.sin(2 * np.pi * station_data['day_of_week'] / 7)
    station_data['day_cos'] = np.cos(2 * np.pi * station_data['day_of_week'] / 7)
    
    station_data[FEATURE_COLS] = scaler.transform(station_data[FEATURE_COLS])
    input_tensor = np.expand_dims(station_data[FEATURE_COLS].values[-LOOKBACK_WINDOW:], axis=0)
    
    pred_scaled = model.predict(input_tensor)
    dummy = np.zeros((1, len(FEATURE_COLS)))
    dummy[0, FEATURE_COLS.index(TARGET_COL)] = pred_scaled[0][0]
    return scaler.inverse_transform(dummy)[0, FEATURE_COLS.index(TARGET_COL)]

# --- MAIN UI ---
model, scaler = load_ai_model()
stations_df = load_stations_with_status() # Updated loader
wards_df = load_wards()

# --- SIDEBAR ---
with st.sidebar:
    st.title("🌬️ Aeris Engine")
    st.caption(f"Last Update: Cycle {count}")
    mode = st.radio("Detection Mode:", ["Physical Network", "Virtual Sensor"])
    
    selected_target = None
    is_virtual = False
    
    # Default Map Center (Bangalore)
    current_lat, current_lon = 12.9716, 77.5946
    
    if mode == "Physical Network":
        if not stations_df.empty:
            selected_target = st.selectbox("Select Station:", stations_df['station_name'].unique())
            row = stations_df[stations_df['station_name'] == selected_target].iloc[0]
            current_lat, current_lon = row['lat'], row['lon']
    else:
        is_virtual = True
        if not wards_df.empty:
            selected_target = st.selectbox("Select Ward:", wards_df['ward_name'].unique())
            row = wards_df[wards_df['ward_name'] == selected_target].iloc[0]
            current_lat, current_lon = row['lat'], row['lon']

# --- DASHBOARD HEADER ---
c_head_1, c_head_2 = st.columns([3, 1])
with c_head_1:
    st.title(f"📍 {selected_target.split(',')[0] if selected_target else 'System Idle'}")
with c_head_2:
    if st.button("🚀 Run Analysis", type="primary", use_container_width=True):
        st.session_state.trigger = True

# Initialize State
if 'pred_val' not in st.session_state: st.session_state.pred_val = None
if 'metrics' not in st.session_state: st.session_state.metrics = None
if 'neighbor' not in st.session_state: st.session_state.neighbor = None
if 'trigger' not in st.session_state: st.session_state.trigger = False

# --- LOGIC ENGINE ---
if st.session_state.trigger and selected_target:
    with st.spinner("Fusion Engine Running..."):
        # 1. PHYSICAL PATH
        if not is_virtual:
            st.session_state.metrics = get_detailed_metrics(selected_target)
            st.session_state.pred_val = run_prediction(selected_target, model, scaler)
            st.session_state.neighbor = None
            
        # 2. VIRTUAL PATH
        else:
            row = wards_df[wards_df['ward_name'] == selected_target].iloc[0]
            input_tensor, neighbor = generate_virtual_input(row['lat'], row['lon'], stations_df, scaler)
            st.session_state.neighbor = neighbor
            
            # For Virtual, we fetch the NEIGHBOR's history to show as reference
            st.session_state.metrics = get_detailed_metrics(neighbor) 
            
            if input_tensor is not None:
                pred_scaled = model.predict(input_tensor)
                dummy = np.zeros((1, len(FEATURE_COLS)))
                dummy[0, FEATURE_COLS.index(TARGET_COL)] = pred_scaled[0][0]
                st.session_state.pred_val = scaler.inverse_transform(dummy)[0, FEATURE_COLS.index(TARGET_COL)]
            
    st.session_state.trigger = False # Reset trigger

# --- DISPLAY LAYER ---
if st.session_state.pred_val is not None:
    
    # 1. METRICS ROW
    m = st.session_state.metrics
    pred = st.session_state.pred_val
    
    # Calculate Delta
    delta_val = None
    if m and m['current'] and m['prev']:
        delta_val = round(m['current'] - m['prev'], 2)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # AQI Display Logic
        if is_virtual:
            st.metric("Virtual PM2.5", "--", "Simulated Node")
        else:
            current_aqi = m['current'] if m and m['current'] else "Offline"
            st.metric("Current PM2.5", f"{current_aqi}", delta=delta_val, delta_color="inverse")
            
    with col2:
        # Traffic Logic
        trf = m['traffic'] if m and m['traffic'] else "--"
        st.metric("Traffic Flow", f"{trf} km/h")
        
    with col3:
        # Prediction Logic
        st.metric("AI Forecast (1 Hr)", f"{pred:.1f} µg/m³", "Future Trend")
        
    with col4:
        # Status Card
        status = "Good"
        color = "#00CC96"
        if pred > 60: status, color = "Moderate", "#FFA500"
        if pred > 90: status, color = "Poor", "#FF4B4B"
        st.markdown(f"""
            <div style="background-color:{color}; padding:10px; border-radius:10px; text-align:center;">
                <h3 style="color:white; margin:0;">{status}</h3>
                <p style="color:white; margin:0; font-size:0.8rem">Air Quality Index</p>
            </div>
        """, unsafe_allow_html=True)

    if is_virtual and st.session_state.neighbor:
        st.info(f"📡 Virtual Sensor Active: Data Interpolated from **{st.session_state.neighbor}** (Nearest Neighbor)")

    # 2. EVIDENCE GRAPH (Trend Line)
    st.markdown("### 📉 Historical Trend & Forecast")
    
    if m and not m['history'].empty:
        hist_df = m['history']
        
        fig_trend = go.Figure()
        
        # Historical Line
        fig_trend.add_trace(go.Scatter(
            x=hist_df['time'], 
            y=hist_df['pollutant_avg'],
            mode='lines+markers',
            name='Historical Data',
            line=dict(color='#00CC96', width=3)
        ))
        
        # Forecast Point
        last_time = hist_df.iloc[-1]['time']
        future_time = last_time + timedelta(hours=1)
        
        fig_trend.add_trace(go.Scatter(
            x=[last_time, future_time],
            y=[hist_df.iloc[-1]['pollutant_avg'], pred],
            mode='lines+markers',
            name='AI Prediction',
            line=dict(color='#FF4B4B', width=3, dash='dot')
        ))
        
        fig_trend.update_layout(
            height=300, 
            margin=dict(l=20, r=20, t=20, b=20),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis_title="Time",
            yaxis_title="PM2.5 Level"
        )
        st.plotly_chart(fig_trend, use_container_width=True)

st.markdown("---")

# --- 3. LIVE MAP (Color Coded) ---
st.markdown("### 🗺️ Live Monitoring Network")

map_df = stations_df.copy()

# Add Status Color Column based on Live AQI
def get_color(aqi):
    if aqi is None: return "#808080" # Grey (Offline)
    if aqi <= 30: return "#00CC96"   # Green
    if aqi <= 60: return "#FFA500"   # Orange
    return "#FF4B4B"                 # Red

map_df['color'] = map_df['latest_aqi'].apply(get_color)
map_df['size'] = 12

# Add Selected Target to Map
if selected_target:
    if is_virtual:
        # Add Virtual Node
        new_row = pd.DataFrame([{
            'station_name': f"{selected_target} (Virtual)",
            'lat': current_lat, 'lon': current_lon,
            'latest_aqi': st.session_state.pred_val if st.session_state.pred_val else 0,
            'color': '#3366FF', # Blue for Virtual
            'size': 20
        }])
        map_df = pd.concat([map_df, new_row], ignore_index=True)
    else:
        # Highlight Physical Node
        mask = map_df['station_name'] == selected_target
        map_df.loc[mask, 'size'] = 25
        map_df.loc[mask, 'color'] = '#3366FF' # Blue highlight

fig_map = px.scatter_mapbox(
    map_df,
    lat="lat", lon="lon",
    hover_name="station_name",
    hover_data={"latest_aqi": True, "lat": False, "lon": False, "color": False, "size": False},
    color_discrete_sequence=map_df['color'].tolist(), # Apply row-specific colors
    size="size",
    zoom=12,
    height=500
)

fig_map.update_layout(
    mapbox_style="carto-darkmatter", # Dark mode map
    mapbox_center={"lat": current_lat, "lon": current_lon},
    margin={"r":0,"t":0,"l":0,"b":0},
    showlegend=False
)

st.plotly_chart(fig_map, use_container_width=True)