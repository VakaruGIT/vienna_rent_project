import pandas as pd
import re  # The "Regex" library - essential for scraping
import os

# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
# Build path relative to script location
data_path = os.path.join(script_dir, "..", "data", "vienna_rent.csv")

# 1. LOAD THE RAW ORE
df = pd.read_csv(data_path)

# Function to extract Price
def extract_price(text):
    # Regex Logic: Look for '€', optional space, then digits/dots/commas
    match = re.search(r'€\s*([\d.,]+)', text)
    if match:
        raw_num = match.group(1)
        # German format: 1.500,00 -> Python format: 1500.00
        clean_num = raw_num.replace('.', '').replace(',', '.')
        return float(clean_num)
    return None

# Function to extract Size
def extract_size(text):
    # Regex Logic: Look for digits before 'm²'
    match = re.search(r'(\d+)\s*m²', text)
    if match:
        return float(match.group(1))
    return None

# Function to extract District (The most valuable feature)
def extract_district(text):
    # Regex Logic: Look for 4 digits starting with 1 (e.g., 1030)
    match = re.search(r'(1\d{3})', text)
    if match:
        return int(match.group(1))
    return None

# Function to extract Rooms (Standard metric)
def extract_rooms(text):
    # Match: "2 Zimmer", "2-Zimmer", "2 Zi", etc.
    match = re.search(r'(\d+)[-\s]*(?:Zimmer|Zi\b)', text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None

# Function to detect Outdoor Space (Value driver)
def has_outdoor(text):
    # Common Vienna outdoor keywords
    keywords = ['balkon', 'terrasse', 'loggia', 'garten', 'dachterrasse', 'freifläche']
    text_lower = text.lower()
    return 1 if any(word in text_lower for word in keywords) else 0

# Function to detect New Building (Premium factor)
def is_new_building(text):
    return 1 if 'neubau' in text.lower() else 0

# Function to extract Floor Level (Affects price)
def extract_floor(text):
    text_lower = text.lower()
    # Check for ground floor variants
    if any(term in text_lower for term in ['erdgeschoss', 'eg', 'hochparterre']):
        return 0
    # Look for floor number: "1. Stock", "2. OG", "3. Etage"
    match = re.search(r'(\d+)\.?\s*(?:stock|og|etage|obergeschoss)', text_lower)
    if match:
        return int(match.group(1))
    return None

# Function to detect Temporary Lease (Usually cheaper)
def is_temporary(text):
    keywords = ['befristet', 'zeitlich begrenzt', 'temporary']
    text_lower = text.lower()
    return 1 if any(word in text_lower for word in keywords) else 0

# Function to detect Furnished (Usually more expensive)
def is_furnished(text):
    keywords = ['möbliert', 'furnished', 'möbel', 'eingerichtet']
    text_lower = text.lower()
    return 1 if any(word in text_lower for word in keywords) else 0

# 2. APPLY THE REFINERY
print("Cleaning data...")
print("Extracting basic features...")

df['price'] = df['raw_text'].apply(extract_price)
df['size'] = df['raw_text'].apply(extract_size)
df['district'] = df['raw_text'].apply(extract_district)

print("Extracting smart features...")
df['rooms'] = df['raw_text'].apply(extract_rooms)
df['has_outdoor'] = df['raw_text'].apply(has_outdoor)
df['is_neubau'] = df['raw_text'].apply(is_new_building)
df['floor'] = df['raw_text'].apply(extract_floor)
df['is_temporary'] = df['raw_text'].apply(is_temporary)
df['is_furnished'] = df['raw_text'].apply(is_furnished)

# 3. CALCULATE METRICS (The "Insight")
# Create a price per m² column
df['price_per_m2'] = df['price'] / df['size']

# 4. ANALYSIS - Show Value Drivers
print("\n" + "="*60)
print("INSIGHTS: What drives rent prices in Vienna?")
print("="*60)

# Insight 1: Outdoor space premium
if df['has_outdoor'].sum() > 0:
    outdoor_comparison = df.groupby('has_outdoor')['price_per_m2'].mean()
    print(f"\n📊 Outdoor Space Impact:")
    print(f"   Without outdoor: €{outdoor_comparison.get(0, 0):.2f}/m²")
    print(f"   With outdoor:    €{outdoor_comparison.get(1, 0):.2f}/m²")
    if len(outdoor_comparison) == 2:
        premium = ((outdoor_comparison[1] / outdoor_comparison[0]) - 1) * 100
        print(f"   Premium: {premium:+.1f}%")

# Insight 2: New building premium
if df['is_neubau'].sum() > 0:
    neubau_comparison = df.groupby('is_neubau')['price_per_m2'].mean()
    print(f"\n🏗️  Building Type Impact:")
    print(f"   Altbau (old):  €{neubau_comparison.get(0, 0):.2f}/m²")
    print(f"   Neubau (new):  €{neubau_comparison.get(1, 0):.2f}/m²")
    if len(neubau_comparison) == 2:
        premium = ((neubau_comparison[1] / neubau_comparison[0]) - 1) * 100
        print(f"   Premium: {premium:+.1f}%")

# Insight 3: Furnished premium
if df['is_furnished'].sum() > 0:
    furnished_comparison = df.groupby('is_furnished')['price'].mean()
    print(f"\n🛋️  Furnished Impact:")
    print(f"   Unfurnished: €{furnished_comparison.get(0, 0):.0f}")
    print(f"   Furnished:   €{furnished_comparison.get(1, 0):.0f}")
    if len(furnished_comparison) == 2:
        premium = ((furnished_comparison[1] / furnished_comparison[0]) - 1) * 100
        print(f"   Premium: {premium:+.1f}%")

# Insight 4: Room distribution
print(f"\n🚪 Room Distribution:")
room_counts = df['rooms'].value_counts().sort_index()
for rooms, count in room_counts.items():
    if pd.notna(rooms):
        avg_price = df[df['rooms'] == rooms]['price'].mean()
        print(f"   {int(rooms)} rooms: {count} listings (avg €{avg_price:.0f})")

# Insight 5: Most common features
print(f"\n📈 Feature Coverage:")
print(f"   Listings with outdoor space: {df['has_outdoor'].sum()} ({df['has_outdoor'].sum()/len(df)*100:.1f}%)")
print(f"   Neubau properties: {df['is_neubau'].sum()} ({df['is_neubau'].sum()/len(df)*100:.1f}%)")
print(f"   Furnished: {df['is_furnished'].sum()} ({df['is_furnished'].sum()/len(df)*100:.1f}%)")
print(f"   Temporary lease: {df['is_temporary'].sum()} ({df['is_temporary'].sum()/len(df)*100:.1f}%)")

print("\n" + "="*60)

# 5. INSPECT SAMPLE
print("\n📋 Sample of cleaned data:")
display_cols = ['district', 'rooms', 'size', 'price', 'price_per_m2', 'has_outdoor', 'is_neubau']
print(df[display_cols].head(10))

# 6. SAVE
output_path = os.path.join(script_dir, "..", "data", "vienna_rent_clean.csv")
df.to_csv(output_path, index=False)
print(f"\n✅ Cleaned data saved to: {output_path}")
print(f"   Total listings: {len(df)}")
print(f"   Columns: {len(df.columns)}")
