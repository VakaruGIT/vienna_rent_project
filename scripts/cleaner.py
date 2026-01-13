import pandas as pd
import re
import os
import hashlib

# Setup paths
script_dir = os.path.dirname(os.path.abspath(__file__))
raw_path = os.path.join(script_dir, "..", "data", "vienna_rent_raw.csv")
clean_path = os.path.join(script_dir, "..", "data", "vienna_rent_clean.csv")

if not os.path.exists(raw_path):
    print("ERROR: Raw data file not found.")
    exit(1)

df = pd.read_csv(raw_path)

# --- EXTRACTION FUNCTIONS ---

def extract_price(text):
    match = re.search(r'€\s*([\d.,]+)', text)
    if match:
        clean_num = match.group(1).replace('.', '').replace(',', '.')
        return float(clean_num)
    return None

def extract_size(text):
    match = re.search(r'(\d+)\s*m²', text)
    if match:
        return float(match.group(1))
    return None

def extract_district(text):
    match = re.search(r'(1\d{3})', text)
    if match:
        return int(match.group(1))
    return None

def extract_rooms(text):
    match = re.search(r'(\d+)\s*(?:Zimmer|Zi)', text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None

def has_outdoor(text):
    keywords = ['balkon', 'terrasse', 'loggia', 'garten', 'dachhaut']
    text_lower = text.lower()
    for word in keywords:
        if word in text_lower:
            return 1
    return 0

def is_neubau(text):
    if 'neubau' in text.lower():
        return 1
    return 0

def create_fingerprint(row):
    # Unique ID based on physical attributes
    unique_string = f"{row['district']}_{row['size']}_{row['rooms']}_{row['price']}"
    return hashlib.md5(unique_string.encode()).hexdigest()[:10]

# --- EXECUTION ---
print("Cleaning data...")

df['price'] = df['raw_text'].apply(extract_price)
df['size'] = df['raw_text'].apply(extract_size)
df['district'] = df['raw_text'].apply(extract_district)
df['rooms'] = df['raw_text'].apply(extract_rooms)
df['has_outdoor'] = df['raw_text'].apply(has_outdoor)
df['is_neubau'] = df['raw_text'].apply(is_neubau)

# Calculate metrics
df['price_per_m2'] = df['price'] / df['size']

# Create Fingerprint for tracking
print("Generating property fingerprints...")
df['fingerprint'] = df.apply(create_fingerprint, axis=1)

# Drop invalid rows
df = df.dropna(subset=['price', 'size', 'district'])

# Save
df.to_csv(clean_path, index=False)
print(f"Data cleaned and saved to: {clean_path}")
print(f"Valid rows: {len(df)}")