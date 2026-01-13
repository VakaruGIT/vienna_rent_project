#!/usr/bin/env python3
"""Quick test to verify geospatial features are working"""

import pandas as pd
import pickle

print("=" * 60)
print("GEOSPATIAL FEATURES - VERIFICATION TEST")
print("=" * 60)

# 1. Check data has new columns
df = pd.read_csv('data/vienna_rent_clean.csv')
print("\n✓ Data loaded:", len(df), "listings")

required_cols = ['dist_center', 'dist_ubahn']
for col in required_cols:
    if col in df.columns:
        print(f"✓ Column '{col}' exists")
        print(f"  Range: {df[col].min():.2f} - {df[col].max():.2f} km")
    else:
        print(f"✗ Column '{col}' MISSING!")

# 2. Check model can use new features
with open('models/rent_price_model.pkl', 'rb') as f:
    model = pickle.load(f)

print("\n✓ Model loaded successfully")
print(f"  Features expected: {model.n_features_in_}")

# 3. Test prediction with geospatial features
test_row = df.iloc[0]
features = ['size', 'rooms', 'district', 'has_outdoor', 'is_neubau', 'is_furnished', 'dist_center', 'dist_ubahn']

print("\n🧪 Test Prediction:")
print(f"  District: {int(test_row['district'])}")
print(f"  Size: {test_row['size']}m²")
print(f"  Distance to center: {test_row['dist_center']:.2f} km")
print(f"  Distance to U-Bahn: {test_row['dist_ubahn']:.2f} km")

input_data = [[test_row[f] for f in features]]
prediction = model.predict(input_data)[0]

print(f"\n  Predicted rent: €{prediction:.0f}")
print(f"  Actual rent: €{test_row['price']:.0f}")
print(f"  Difference: €{abs(prediction - test_row['price']):.0f}")

# 4. Show top insights
print("\n📊 Geospatial Insights:")
print("\nMost Central Districts:")
central = df.groupby('district')['dist_center'].mean().sort_values().head(3)
for dist, km in central.items():
    print(f"  {int(dist)}: {km:.2f} km from Stephansplatz")

print("\nBest U-Bahn Access:")
ubahn = df.groupby('district')['dist_ubahn'].mean().sort_values().head(3)
for dist, km in ubahn.items():
    print(f"  {int(dist)}: {km:.2f} km to nearest station")

print("\n" + "=" * 60)
print("✓ ALL TESTS PASSED - Geospatial features working!")
print("=" * 60)
