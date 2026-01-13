import pandas as pd
import os
from datetime import datetime

script_dir = os.path.dirname(os.path.abspath(__file__))
clean_path = os.path.join(script_dir, "..", "data", "vienna_rent_clean.csv")
history_path = os.path.join(script_dir, "..", "data", "vienna_rent_history.csv")

print("-" * 60)
print("HISTORICAL TRACKER")
print("-" * 60)

if not os.path.exists(clean_path):
    print(f"ERROR: {clean_path} not found")
    exit(1)

df_today = pd.read_csv(clean_path)
df_today['snapshot_date'] = datetime.now().strftime('%Y-%m-%d')

# Load History
if os.path.exists(history_path):
    df_history = pd.read_csv(history_path)
    print(f"Existing history: {len(df_history)} records")
    
    # --- INTELLIGENT TRACKING ---
    if 'fingerprint' in df_history.columns:
        history_fingerprints = set(df_history['fingerprint'])
        history_links = set(df_history['link'])
        
        # 1. True New Listings (New Physical Property)
        true_new = df_today[~df_today['fingerprint'].isin(history_fingerprints)]
        
        # 2. Re-uploads (Old Property, New Link)
        reuploads = df_today[
            (df_today['fingerprint'].isin(history_fingerprints)) & 
            (~df_today['link'].isin(history_links))
        ]
        
        if not true_new.empty:
            print(f"\nALERT: {len(true_new)} TRULY NEW LISTINGS FOUND")
            # Show inner city deals
            deals = true_new[
                (true_new['district'].isin([1010, 1020, 1030, 1040, 1050, 1060, 1070])) & 
                (true_new['price'] < 1000)
            ]
            if not deals.empty:
                print("POSSIBLE DEALS (Inner Districts < 1000 Euro):")
                for _, row in deals.iterrows():
                    print(f" - {row['price']} Euro | {row['district']} | {row['size']}m2 | {row['link']}")
        
        if not reuploads.empty:
            print(f"\nINFO: Detected {len(reuploads)} re-uploaded ads (same flat, new link).")
            
    else:
        print("Legacy history file detected. Fingerprints will be added.")

    # Combine
    df_combined = pd.concat([df_history, df_today], ignore_index=True)
    
    # DEDUPLICATION
    # If fingerprint exists multiple times, keep the LAST one (most recent link/date)
    before_dedup = len(df_combined)
    df_combined = df_combined.sort_values('snapshot_date')
    df_combined = df_combined.drop_duplicates(subset=['fingerprint'], keep='last')
    
    print(f"Database updated. Total unique active listings: {len(df_combined)}")

else:
    print("Creating new history file.")
    df_combined = df_today

# Save
df_combined.to_csv(history_path, index=False)
print("-" * 60)
print("TRACKING COMPLETE")
print("-" * 60)