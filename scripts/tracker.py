"""
Historical Tracker - Appends today's clean data to long-term database
Run this after scraper.py + cleaner.py to maintain historical timeline
"""

import pandas as pd
import os
from datetime import datetime

# Get script directory for relative paths
script_dir = os.path.dirname(os.path.abspath(__file__))
clean_path = os.path.join(script_dir, "..", "data", "vienna_rent_clean.csv")
history_path = os.path.join(script_dir, "..", "data", "vienna_rent_history.csv")

print("=" * 70)
print("HISTORICAL TRACKER - Adding today's data to timeline")
print("=" * 70)

# 1. Load today's clean data
if not os.path.exists(clean_path):
    print(f"❌ Error: {clean_path} not found")
    print("   Run cleaner.py first!")
    exit(1)

df_today = pd.read_csv(clean_path)
df_today['snapshot_date'] = datetime.now().strftime('%Y-%m-%d')

print(f"\n📊 Today's data loaded: {len(df_today)} listings")

# 2. Load or create history
if os.path.exists(history_path):
    df_history = pd.read_csv(history_path)
    print(f"📚 Existing history: {len(df_history):,} records")
    
    # Append today's data
    df_combined = pd.concat([df_history, df_today], ignore_index=True)
    
    # Remove duplicates (same listing on same day)
    before_dedup = len(df_combined)
    df_combined = df_combined.drop_duplicates(subset=['link', 'snapshot_date'], keep='last')
    dedup_count = before_dedup - len(df_combined)
    
    if dedup_count > 0:
        print(f"🔄 Removed {dedup_count} duplicate entries")
    
else:
    print("📝 Creating new history file (first run)")
    df_combined = df_today

# 3. Calculate insights
unique_listings = df_combined['link'].nunique()
date_range_start = df_combined['snapshot_date'].min()
date_range_end = df_combined['snapshot_date'].max()
total_snapshots = df_combined['snapshot_date'].nunique()

# 4. Save
df_combined.to_csv(history_path, index=False)

print("\n" + "=" * 70)
print("✅ HISTORY UPDATED SUCCESSFULLY")
print("=" * 70)
print(f"\nToday's listings added:        {len(df_today)}")
print(f"Total historical records:      {len(df_combined):,}")
print(f"Unique listings ever seen:     {unique_listings:,}")
print(f"Total snapshots (days):        {total_snapshots}")
print(f"Date range:                    {date_range_start} → {date_range_end}")

# 5. Per-district breakdown
if len(df_today) > 0:
    district_today = df_today['district'].value_counts().head(5)
    print(f"\n📍 Top districts today:")
    for district, count in district_today.items():
        print(f"   {district}: {count} listings")

# 6. Price trends (if we have multiple days)
if total_snapshots > 1:
    print(f"\n📈 Historical trends available:")
    print(f"   {len(df_combined):,} records across {total_snapshots} days")
    print(f"   Use this data for ML training and market analysis!")

print("\n" + "=" * 70)
print("NEXT STEPS:")
print("=" * 70)
print("• Run this daily to build your historical database")
print("• Use vienna_rent_history.csv for ML training")
print("• Analyze trends: price changes, seasonal patterns, listing velocity")
print("=" * 70)
