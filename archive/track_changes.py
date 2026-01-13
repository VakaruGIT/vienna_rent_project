"""
TEMPORAL TRACKING SYSTEM - Handles listing lifecycle

This system tracks:
1. New listings (first appearance)
2. Active listings (still on market)
3. Price changes (same listing, different price)
4. Removed listings (rented out or pulled)
5. Days on market (time until rented)

Database structure:
- vienna_rent_history.csv: Complete timeline (append-only)
- vienna_rent_active.csv: Current active listings only
- vienna_rent_removed.csv: Historical removed listings

Each scrape creates a snapshot with:
- listing_id (extracted from URL)
- scrape_date
- status (new/active/price_changed/removed)
- days_on_market
- price_history
"""

import pandas as pd
import os
from datetime import datetime, timedelta
import hashlib

script_dir = os.path.dirname(os.path.abspath(__file__))
history_path = os.path.join(script_dir, "..", "data", "vienna_rent_history.csv")
active_path = os.path.join(script_dir, "..", "data", "vienna_rent_active.csv")
removed_path = os.path.join(script_dir, "..", "data", "vienna_rent_removed.csv")
raw_path = os.path.join(script_dir, "..", "data", "vienna_rent.csv")

def extract_listing_id(url):
    """
    Extract unique ID from willhaben URL
    Example: https://willhaben.at/iad/immobilien/d/mietwohnung/1234567890
    Returns: 1234567890
    """
    import re
    match = re.search(r'/d/[^/]+/(\d+)', url)
    if match:
        return match.group(1)
    # Fallback: hash the URL
    return hashlib.md5(url.encode()).hexdigest()[:12]

def load_historical_data():
    """Load all historical tracking data"""
    if os.path.exists(history_path):
        df = pd.read_csv(history_path)
        df['scrape_date'] = pd.to_datetime(df['scrape_date'])
        return df
    return pd.DataFrame()

def load_active_listings():
    """Load currently active listings (from last scrape)"""
    if os.path.exists(active_path):
        df = pd.read_csv(active_path)
        df['first_seen'] = pd.to_datetime(df['first_seen'])
        df['last_seen'] = pd.to_datetime(df['last_seen'])
        return df
    return pd.DataFrame()

def process_temporal_tracking():
    """
    Main tracking logic - compares new scrape with historical data
    """
    print("="*70)
    print("TEMPORAL TRACKING SYSTEM - Analyzing Listing Lifecycle")
    print("="*70)
    
    # Load new scrape data
    if not os.path.exists(raw_path):
        print("\nERROR: No scrape data found. Run scraper.py first.")
        return
    
    new_scrape = pd.read_csv(raw_path)
    scrape_date = datetime.now()
    
    # Extract listing IDs
    new_scrape['listing_id'] = new_scrape['link'].apply(extract_listing_id)
    
    print(f"\nNew scrape: {len(new_scrape)} listings at {scrape_date.strftime('%Y-%m-%d %H:%M')}")
    
    # Load historical data
    history = load_historical_data()
    active = load_active_listings()
    
    # Initialize tracking columns
    new_scrape['scrape_date'] = scrape_date
    new_scrape['status'] = 'unknown'
    new_scrape['first_seen'] = scrape_date
    new_scrape['last_seen'] = scrape_date
    new_scrape['days_on_market'] = 0
    new_scrape['price_change'] = 0.0
    new_scrape['price_change_pct'] = 0.0
    
    # Analysis counters
    truly_new = 0
    still_active = 0
    price_changed = 0
    removed_count = 0
    
    # === IDENTIFY NEW vs EXISTING LISTINGS ===
    if len(active) > 0:
        existing_ids = set(active['listing_id'])
        
        for idx, row in new_scrape.iterrows():
            listing_id = row['listing_id']
            
            if listing_id in existing_ids:
                # EXISTING LISTING - still active
                prev_data = active[active['listing_id'] == listing_id].iloc[0]
                
                new_scrape.at[idx, 'status'] = 'active'
                new_scrape.at[idx, 'first_seen'] = prev_data['first_seen']
                new_scrape.at[idx, 'last_seen'] = scrape_date
                
                # Calculate days on market
                first_seen = pd.to_datetime(prev_data['first_seen'])
                days_on_market = (scrape_date - first_seen).days
                new_scrape.at[idx, 'days_on_market'] = days_on_market
                
                # Check for price changes
                if pd.notna(row['price']) and pd.notna(prev_data['price']):
                    old_price = prev_data['price']
                    new_price = row['price']
                    
                    if abs(new_price - old_price) > 1:  # More than €1 difference
                        price_diff = new_price - old_price
                        price_diff_pct = (price_diff / old_price) * 100
                        
                        new_scrape.at[idx, 'status'] = 'price_changed'
                        new_scrape.at[idx, 'price_change'] = price_diff
                        new_scrape.at[idx, 'price_change_pct'] = price_diff_pct
                        price_changed += 1
                
                still_active += 1
            else:
                # NEW LISTING - first time seeing it
                new_scrape.at[idx, 'status'] = 'new'
                truly_new += 1
    else:
        # First run - everything is new
        new_scrape['status'] = 'new'
        truly_new = len(new_scrape)
    
    # === IDENTIFY REMOVED LISTINGS ===
    if len(active) > 0:
        current_ids = set(new_scrape['listing_id'])
        previous_ids = set(active['listing_id'])
        removed_ids = previous_ids - current_ids
        
        if len(removed_ids) > 0:
            removed_listings = active[active['listing_id'].isin(removed_ids)].copy()
            removed_listings['status'] = 'removed'
            removed_listings['removed_date'] = scrape_date
            removed_listings['last_seen'] = scrape_date
            
            # Calculate final days on market
            removed_listings['days_on_market'] = (
                scrape_date - pd.to_datetime(removed_listings['first_seen'])
            ).dt.days
            
            removed_count = len(removed_listings)
            
            # Append to removed listings archive
            if os.path.exists(removed_path):
                existing_removed = pd.read_csv(removed_path)
                all_removed = pd.concat([existing_removed, removed_listings], ignore_index=True)
            else:
                all_removed = removed_listings
            
            all_removed.to_csv(removed_path, index=False)
    
    # === SAVE RESULTS ===
    
    # 1. Append to history (complete timeline)
    if os.path.exists(history_path):
        history = pd.read_csv(history_path)
        history = pd.concat([history, new_scrape], ignore_index=True)
    else:
        history = new_scrape
    
    history.to_csv(history_path, index=False)
    
    # 2. Update active listings (current snapshot)
    new_scrape.to_csv(active_path, index=False)
    
    # === REPORT ===
    print("\n" + "="*70)
    print("TRACKING RESULTS")
    print("="*70)
    
    print(f"\nListing Status:")
    print(f"  New listings (first appearance):  {truly_new}")
    print(f"  Still active (no change):         {still_active}")
    print(f"  Price changes detected:           {price_changed}")
    print(f"  Removed/Rented:                   {removed_count}")
    
    if price_changed > 0:
        print(f"\nPrice Changes:")
        price_changes = new_scrape[new_scrape['status'] == 'price_changed']
        for _, row in price_changes.head(5).iterrows():
            direction = "↑" if row['price_change'] > 0 else "↓"
            print(f"  {direction} District {row['district']:.0f}: €{abs(row['price_change']):.0f} "
                  f"({row['price_change_pct']:+.1f}%) - {row['days_on_market']} days on market")
    
    if removed_count > 0:
        print(f"\nRemoved Listings (Likely Rented):")
        removed_listings = pd.read_csv(removed_path)
        recent_removed = removed_listings.tail(5)
        for _, row in recent_removed.iterrows():
            print(f"  District {row['district']:.0f}: {row['rooms']:.0f}R, {row['size']:.0f}m², "
                  f"€{row['price']:.0f} - Lasted {row['days_on_market']} days")
    
    # === MARKET INSIGHTS ===
    print("\n" + "="*70)
    print("MARKET INSIGHTS")
    print("="*70)
    
    # Days on market analysis
    if len(new_scrape[new_scrape['days_on_market'] > 0]) > 0:
        avg_days = new_scrape[new_scrape['days_on_market'] > 0]['days_on_market'].mean()
        print(f"\nAverage time on market: {avg_days:.1f} days")
        
        # Identify "hot" listings (rented quickly)
        if removed_count > 0:
            removed_data = pd.read_csv(removed_path)
            fast_rentals = removed_data[removed_data['days_on_market'] <= 3]
            if len(fast_rentals) > 0:
                print(f"\nHot market indicator: {len(fast_rentals)} listings rented in ≤3 days")
                print(f"  Avg price of fast rentals: €{fast_rentals['price'].mean():.0f}")
    
    # Price trend detection
    if price_changed > 0:
        price_increases = len(new_scrape[new_scrape['price_change'] > 0])
        price_decreases = len(new_scrape[new_scrape['price_change'] < 0])
        
        print(f"\nPrice movement:")
        print(f"  Increases: {price_increases} ({price_increases/price_changed*100:.1f}%)")
        print(f"  Decreases: {price_decreases} ({price_decreases/price_changed*100:.1f}%)")
        
        if price_decreases > price_increases:
            print(f"  → Market softening detected (more price drops)")
        elif price_increases > price_decreases:
            print(f"  → Market heating up (more price increases)")
    
    print("\n" + "="*70)
    print("FILES UPDATED")
    print("="*70)
    print(f"\nHistory (complete timeline):  {history_path}")
    print(f"  Total records: {len(history)}")
    print(f"\nActive listings (current):    {active_path}")
    print(f"  Total active: {len(new_scrape)}")
    print(f"\nRemoved listings (archived):  {removed_path}")
    if os.path.exists(removed_path):
        removed_df = pd.read_csv(removed_path)
        print(f"  Total removed: {len(removed_df)}")
    
    print("\n" + "="*70)
    print("RUN THIS DAILY TO TRACK MARKET DYNAMICS")
    print("="*70)

if __name__ == "__main__":
    process_temporal_tracking()
