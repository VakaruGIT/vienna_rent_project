import pandas as pd
import pickle
import os
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score, mean_squared_error
import numpy as np

# Get script directory for relative paths
script_dir = os.path.dirname(os.path.abspath(__file__))
data_path = os.path.join(script_dir, "..", "data", "vienna_rent_clean.csv")
model_path = os.path.join(script_dir, "..", "models", "rent_price_model.pkl")

print("="*60)
print("VIENNA RENT PRICE PREDICTOR - TRAINING")
print("="*60)

# 1. LOAD DATA
df = pd.read_csv(data_path)
print(f"\nLoaded {len(df)} listings")

# 2. FEATURE ENGINEERING
# Note: Removed 'floor' due to low coverage (only 11.7% of listings have this data)
features = ['size', 'rooms', 'district', 'has_outdoor', 'is_neubau', 'is_furnished']
target = 'price'

# Check feature availability
print(f"\nFeature availability:")
for feat in features:
    if feat in df.columns:
        missing = df[feat].isna().sum()
        print(f"   {feat:15s}: {len(df) - missing}/{len(df)} values ({(len(df)-missing)/len(df)*100:.1f}%)")
    else:
        print(f"   {feat:15s}: NOT FOUND")

# Drop rows with missing critical data
df_clean = df.dropna(subset=features + [target])
print(f"\nAfter cleaning: {len(df_clean)} usable listings ({len(df_clean)/len(df)*100:.1f}% of total)")

if len(df_clean) < 30:
    print("\nWARNING: Too few samples for reliable training!")
    print("Consider collecting more data or using fewer features.")
    exit(1)

X = df_clean[features]
y = df_clean[target]

# Show target statistics
print(f"\nTarget variable (price) statistics:")
print(f"   Mean: €{y.mean():.2f}")
print(f"   Median: €{y.median():.2f}")
print(f"   Min: €{y.min():.2f}")
print(f"   Max: €{y.max():.2f}")
print(f"   Std Dev: €{y.std():.2f}")

# 3. TRAIN-TEST SPLIT
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)
print(f"\nTrain set: {len(X_train)} samples")
print(f"Test set:  {len(X_test)} samples")

# 4. TRAIN MODEL
print("\n" + "-"*60)
print("Training Random Forest model...")
print("-"*60)

model = RandomForestRegressor(
    n_estimators=200,
    max_depth=15,
    min_samples_split=5,
    min_samples_leaf=2,
    random_state=42,
    n_jobs=-1,
    verbose=0
)
model.fit(X_train, y_train)
print("Model training complete!")

# 5. EVALUATE
print("\n" + "="*60)
print("MODEL PERFORMANCE")
print("="*60)

# Training performance
y_train_pred = model.predict(X_train)
train_mae = mean_absolute_error(y_train, y_train_pred)
train_r2 = r2_score(y_train, y_train_pred)

# Test performance
y_test_pred = model.predict(X_test)
test_mae = mean_absolute_error(y_test, y_test_pred)
test_rmse = np.sqrt(mean_squared_error(y_test, y_test_pred))
test_r2 = r2_score(y_test, y_test_pred)

print(f"\nTraining Set:")
print(f"   Mean Absolute Error: €{train_mae:.2f}")
print(f"   R² Score: {train_r2:.3f} ({train_r2*100:.1f}% variance explained)")

print(f"\nTest Set (Unseen Data):")
print(f"   Mean Absolute Error: €{test_mae:.2f}")
print(f"   Root Mean Squared Error: €{test_rmse:.2f}")
print(f"   R² Score: {test_r2:.3f} ({test_r2*100:.1f}% variance explained)")

# Calculate percentage error
avg_price = y_test.mean()
percent_error = (test_mae / avg_price) * 100
print(f"\nAverage prediction error: {percent_error:.1f}% of actual price")

# 6. FEATURE IMPORTANCE
print("\n" + "="*60)
print("FEATURE IMPORTANCE ANALYSIS")
print("="*60)

feature_importance = pd.DataFrame({
    'feature': features,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)

print("\nWhich factors matter most for predicting rent?")
for idx, row in feature_importance.iterrows():
    bar_length = int(row['importance'] * 50)
    bar = '█' * bar_length
    print(f"   {row['feature']:15s}: {bar} {row['importance']*100:5.1f}%")

# 7. SAMPLE PREDICTIONS
print("\n" + "="*60)
print("SAMPLE PREDICTIONS (Test Set)")
print("="*60)

# Show 5 random predictions
sample_indices = np.random.choice(X_test.index, min(5, len(X_test)), replace=False)
print(f"\n{'Actual':>10s} {'Predicted':>10s} {'Error':>10s} | Features")
print("-" * 60)

for idx in sample_indices:
    actual = y_test.loc[idx]
    predicted = model.predict(X_test.loc[[idx]])[0]
    error = predicted - actual
    
    # Get feature values
    size = X_test.loc[idx, 'size']
    rooms = X_test.loc[idx, 'rooms']
    district = X_test.loc[idx, 'district']
    
    print(f"€{actual:>8.0f} €{predicted:>9.0f} €{error:>9.0f} | {rooms:.0f}R, {size:.0f}m², District {district:.0f}")

# 8. SAVE MODEL
with open(model_path, 'wb') as f:
    pickle.dump(model, f)

# Also save feature names for later use
feature_info = {
    'features': features,
    'feature_importance': dict(zip(features, model.feature_importances_)),
    'test_mae': test_mae,
    'test_r2': test_r2,
    'avg_price': avg_price
}

info_path = os.path.join(script_dir, "..", "data", "model_info.pkl")
with open(info_path, 'wb') as f:
    pickle.dump(feature_info, f)

print("\n" + "="*60)
print("SAVE COMPLETE")
print("="*60)
print(f"\nModel saved to: {model_path}")
print(f"Model info saved to: {info_path}")

print("\n" + "="*60)
print("NEXT STEPS")
print("="*60)
print("""
You can now use this model to:
1. Predict rent for any Vienna apartment
2. Analyze which features drive prices
3. Build a price calculator app (Streamlit)

Example usage:
    import pickle
    with open('data/rent_price_model.pkl', 'rb') as f:
        model = pickle.load(f)
    
    # Predict for: 50m², 2 rooms, district 1050, with balcony
    prediction = model.predict([[50, 2, 1050, 1, 0, 0, 2]])
    print(f"Estimated rent: €{prediction[0]:.0f}")
""")
