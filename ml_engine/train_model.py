import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping
from sklearn.model_selection import train_test_split
import joblib

# Import our custom data pipeline
from preprocessor import fetch_data, preprocess_data, create_sequences

# --- Settings ---
EPOCHS = 20              # How many times to loop through the data
BATCH_SIZE = 16          # How many examples to feed at once
MODEL_PATH = 'aeris_v1.keras'
SCALER_PATH = 'scaler.gz'

# 🛡️ SAFE STATION LIST (Verified from your DB)
SAFE_STATIONS = [
    "BTM Layout, Bengaluru - CPCB",
    "BWSSB Kadabesanahalli, Bengaluru - CPCB",
    "Hebbal, Bengaluru - KSPCB",
    "Hombegowda Nagar, Bengaluru - KSPCB",
    "Jayanagar 5th Block, Bengaluru - KSPCB",
    "Jigani, Bengaluru - KSPCB",
    "Kasturi Nagar, Bengaluru - KSPCB",
    "Peenya, Bengaluru - CPCB",
    "RVCE-Mailasandra, Bengaluru - KSPCB",
    "Silk Board, Bengaluru - KSPCB"
]

def build_model(input_shape):
    """
    Defines the LSTM Neural Network Architecture.
    """
    model = Sequential()
    
    # 1. LSTM Layer
    model.add(LSTM(50, input_shape=input_shape, return_sequences=False))
    
    # 2. Dropout Layer (Prevents overfitting)
    model.add(Dropout(0.2))
    
    # 3. Dense Output Layer
    model.add(Dense(1))
    
    # 4. Compile
    model.compile(optimizer='adam', loss='mse', metrics=['mae'])
    
    return model

if __name__ == "__main__":
    print("🚀 STARTING MODEL TRAINING PIPELINE...")
    
    # 1. Get Data using our existing pipeline
    raw_df = fetch_data()
    
    if raw_df.empty:
        print("❌ Error: Not enough data to train.")
    else:
        # --- 🛡️ SAFETY FILTER START ---
        print(f"🧐 Filtering for {len(SAFE_STATIONS)} original stations...")
        original_count = len(raw_df)
        
        # Keep only rows where 'station_name' is in our Safe List
        raw_df = raw_df[raw_df['station_name'].isin(SAFE_STATIONS)]
        
        filtered_count = len(raw_df)
        print(f"📉 Rows before: {original_count} | Rows after: {filtered_count}")
        
        if filtered_count == 0:
            print("❌ CRITICAL ERROR: Filter removed all data! Check your station names.")
            exit()
        # --- 🛡️ SAFETY FILTER END ---

        # 2. Preprocess
        clean_df, scaler = preprocess_data(raw_df)
        
        # Save the scaler! We need it to translate predictions back to real numbers later.
        joblib.dump(scaler, SCALER_PATH)
        print(f"✅ Scaler saved to {SCALER_PATH}")
        
        # 3. Create Sequences
        X, y = create_sequences(clean_df)
        
        if len(X) == 0:
            print("❌ Error: Not enough data to create sequences. Need > 24 hours.")
        else:
            print(f"✅ Dataset created. Samples: {len(X)}")
            
            # 4. Split Data (80% Train, 20% Test)
            # shuffle=False is crucial for time-series! We generally want to test on the "future".
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
            
            # 5. Build Model
            model = build_model((X.shape[1], X.shape[2]))
            model.summary()
            
            # 6. Train Model
            print("\n🏃 Training started...")
            
            # EarlyStopping stops training if the model stops improving (saves time)
            early_stop = EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True)
            
            history = model.fit(
                X_train, y_train,
                epochs=EPOCHS,
                batch_size=BATCH_SIZE,
                validation_data=(X_test, y_test),
                callbacks=[early_stop],
                verbose=1
            )
            
            # 7. Save the Model
            model.save(MODEL_PATH)
            print(f"\n🎉 SUCCESS! Model saved to {MODEL_PATH}")
            print(f"Final Validation Loss: {history.history['val_loss'][-1]}")