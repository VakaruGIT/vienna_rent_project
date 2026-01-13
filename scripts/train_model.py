import pandas as pd
import pickle
import os
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score

# --- CONFIGURATION ---
MODEL_PATH = "models/rent_price_model.pkl"
HISTORY_PATH = "data/vienna_rent_history.csv"
CLEAN_PATH = "data/vienna_rent_clean.csv"

# Potential features to use (including new geospatial features)
CANDIDATE_FEATURES = [
    'size', 'rooms', 'district', 'has_outdoor', 'is_neubau', 'is_furnished',
    'dist_center',  # Distance to city center (Stephansplatz)
    'dist_ubahn'    # Distance to nearest U-Bahn station
]
TARGET = 'price'
# ---------------------

print("-" * 60)
print("VIENNA RENT PRICE PREDICTOR - TRAINING")
print("-" * 60)

# 1. Load Data (prefer historical, fallback to clean)
script_dir = os.path.dirname(os.path.abspath(__file__))
abs_history_path = os.path.join(script_dir, "..", HISTORY_PATH)
abs_clean_path = os.path.join(script_dir, "..", CLEAN_PATH)
abs_model_path = os.path.join(script_dir, "..", MODEL_PATH)

if os.path.exists(abs_history_path):
    df = pd.read_csv(abs_history_path)
    print(f"✓ Using historical data: {len(df)} total records")
    
    # Deduplicate: keep latest version of each listing
    if 'fingerprint' in df.columns and 'scraped_date' in df.columns:
        df = df.sort_values('scraped_date', ascending=False)
        df = df.drop_duplicates(subset='fingerprint', keep='first')
        print(f"✓ Deduplicated to {len(df)} unique listings")
    elif 'fingerprint' in df.columns:
        df = df.drop_duplicates(subset='fingerprint', keep='last')
        print(f"✓ Deduplicated to {len(df)} unique listings")
    
elif os.path.exists(abs_clean_path):
    df = pd.read_csv(abs_clean_path)
    print(f"⚠ Using daily snapshot (no history): {len(df)} listings")
else:
    print("ERROR: No training data found")
    exit(1)

# 2. Validate Features (CRASH PROOF LOGIC)
available_features = []
print("Checking features...")
for f in CANDIDATE_FEATURES:
    if f in df.columns:
        available_features.append(f)
        print(f"  [OK] {f}")
    else:
        print(f"  [MISSING] {f} (Skipping)")

if not available_features:
    print("ERROR: No valid features found to train on.")
    exit(1)

print(f"Training on: {available_features}")

# 3. Clean Data for Training
# Drop rows where target or features are missing
df_train = df.dropna(subset=available_features + [TARGET])

# Filter outliers (Top 1% most expensive)
p99 = df_train[TARGET].quantile(0.99)
df_train = df_train[df_train[TARGET] < p99]

X = df_train[available_features]
y = df_train[TARGET]

print(f"Training set size after filtering: {len(df_train)}")

# 4. Train Model
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# 5. Evaluate
predictions = model.predict(X_test)
mae = mean_absolute_error(y_test, predictions)
r2 = r2_score(y_test, predictions)

print("-" * 30)
print(f"Model Performance:")
print(f"R2 Score: {r2:.3f}")
print(f"Avg Error: +/- {mae:.2f} Euro")
print("-" * 30)

# Feature importance
print("\nFeature Importance:")
feature_importance = pd.DataFrame({
    'feature': available_features,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)

for _, row in feature_importance.iterrows():
    print(f"  {row['feature']:20s}: {row['importance']*100:5.1f}%")

# 6. Save Model with Metadata
model_package = {
    'model': model,
    'features': available_features,
    'r2_score': r2,
    'mae': mae,
    'trained_on': pd.Timestamp.now().isoformat()
}

with open(abs_model_path, 'wb') as f:
    pickle.dump(model_package, f)

print(f"SUCCESS: Model saved to {MODEL_PATH}")
print(f"Features stored: {available_features}")