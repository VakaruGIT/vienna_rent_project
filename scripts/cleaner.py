import pandas as pd
import pickle
import os
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score

# --- CONFIGURATION ---
MODEL_PATH = "data/rent_price_model.pkl"
DATA_PATH = "data/vienna_rent_clean.csv"

# Potential features to use
CANDIDATE_FEATURES = ['size', 'rooms', 'district', 'has_outdoor', 'is_neubau', 'is_furnished']
TARGET = 'price'
# ---------------------

print("-" * 60)
print("VIENNA RENT PRICE PREDICTOR - TRAINING")
print("-" * 60)

# 1. Load Data
script_dir = os.path.dirname(os.path.abspath(__file__))
abs_data_path = os.path.join(script_dir, "..", DATA_PATH)
abs_model_path = os.path.join(script_dir, "..", MODEL_PATH)

if not os.path.exists(abs_data_path):
    print(f"ERROR: {abs_data_path} not found.")
    exit(1)

df = pd.read_csv(abs_data_path)
print(f"Loaded {len(df)} listings")

# 2. Validate Features
available_features = []
for f in CANDIDATE_FEATURES:
    if f in df.columns:
        available_features.append(f)
    else:
        print(f"WARNING: Feature '{f}' not found in CSV. Skipping.")

if not available_features:
    print("ERROR: No valid features found to train on.")
    exit(1)

print(f"Training on features: {available_features}")

# 3. Clean Data for Training
# Drop rows where target or features are missing
df_train = df.dropna(subset=available_features + [TARGET])

# Filter outliers (Top 1% most expensive) to improve accuracy
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
print(f"R2 Score: {r2:.3f} (0=Bad, 1=Perfect)")
print(f"Avg Error: +/- {mae:.2f} Euro")
print("-" * 30)

# 6. Save Model
with open(abs_model_path, 'wb') as f:
    pickle.dump(model, f)

print(f"SUCCESS: Model saved to {MODEL_PATH}")