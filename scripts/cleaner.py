import pandas as pd
import re
import os
import hashlib
from math import radians, sin, cos, sqrt, atan2

# Setup paths
script_dir = os.path.dirname(os.path.abspath(__file__))
# Read from RAW, Save to CLEAN
raw_path = os.path.join(script_dir, "..", "data", "vienna_rent_raw.csv")
clean_path = os.path.join(script_dir, "..", "data", "vienna_rent_clean.csv")

# --- GEOSPATIAL DATA ---
# Stephansplatz (City Center)
STEPHANSPLATZ = (48.20849, 16.37382)

# District center coordinates
DISTRICT_CENTERS = {
    1010: (48.2082, 16.3738), 1020: (48.2167, 16.4167), 1030: (48.1986, 16.3958),
    1040: (48.1917, 16.3667), 1050: (48.1889, 16.3556), 1060: (48.1950, 16.3500),
    1070: (48.2014, 16.3486), 1080: (48.2111, 16.3472), 1090: (48.2236, 16.3583),
    1100: (48.1561, 16.3814), 1110: (48.1692, 16.4383), 1120: (48.1700, 16.3264),
    1130: (48.1792, 16.2753), 1140: (48.2086, 16.2625), 1150: (48.1967, 16.3256),
    1160: (48.2133, 16.3056), 1170: (48.2289, 16.3056), 1180: (48.2319, 16.3317),
    1190: (48.2561, 16.3361), 1200: (48.2389, 16.3756), 1210: (48.2728, 16.4169),
    1220: (48.2333, 16.4667), 1230: (48.1403, 16.2911)
}

# Major U-Bahn stations (U1, U2, U3, U4, U6 key stations)
UBAHN_STATIONS = [
    (48.2082, 16.3738),  # Stephansplatz (U1/U3)
    (48.2100, 16.3789),  # Schwedenplatz (U1/U4)
    (48.1985, 16.3706),  # Karlsplatz (U1/U2/U4)
    (48.2133, 16.3833),  # Praterstern (U1/U2)
    (48.2267, 16.3803),  # Nestroyplatz (U1)
    (48.1854, 16.3767),  # Südtiroler Platz (U1)
    (48.2389, 16.3756),  # Floridsdorf (U6)
    (48.1906, 16.3389),  # Längenfeldgasse (U4/U6)
    (48.2133, 16.3333),  # Nußdorfer Straße (U6)
    (48.1733, 16.3378),  # Meidling (U4/U6)
]

if not os.path.exists(raw_path):
    print(f"ERROR: Raw data file not found at {raw_path}")
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

def is_furnished(text):
    keywords = ['möbliert', 'einbauküche', 'voll ausgestattet', 'küche']
    text_lower = text.lower()
    for word in keywords:
        if word in text_lower:
            return 1
    return 0

def create_fingerprint(row):
    # Unique ID based on physical attributes
    unique_string = f"{row['district']}_{row['size']}_{row['rooms']}_{row['price']}"
    return hashlib.md5(unique_string.encode()).hexdigest()[:10]

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points on Earth in kilometers"""
    R = 6371.0  # Earth radius in km
    
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    
    a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    
    return R * c

def calculate_dist_center(district_code):
    """Calculate distance from district center to Stephansplatz"""
    if district_code not in DISTRICT_CENTERS:
        return None
    
    lat1, lon1 = STEPHANSPLATZ
    lat2, lon2 = DISTRICT_CENTERS[district_code]
    
    return haversine_distance(lat1, lon1, lat2, lon2)

def calculate_dist_ubahn(district_code):
    """Calculate distance from district center to nearest U-Bahn station"""
    if district_code not in DISTRICT_CENTERS:
        return None
    
    district_lat, district_lon = DISTRICT_CENTERS[district_code]
    
    # Find nearest U-Bahn station
    min_distance = float('inf')
    for station_lat, station_lon in UBAHN_STATIONS:
        dist = haversine_distance(district_lat, district_lon, station_lat, station_lon)
        if dist < min_distance:
            min_distance = dist
    
    return min_distance

# --- EXECUTION ---
print("Cleaning data...")

df['price'] = df['raw_text'].apply(extract_price)
df['size'] = df['raw_text'].apply(extract_size)
df['district'] = df['raw_text'].apply(extract_district)
df['rooms'] = df['raw_text'].apply(extract_rooms)
df['has_outdoor'] = df['raw_text'].apply(has_outdoor)
df['is_neubau'] = df['raw_text'].apply(is_neubau)
df['is_furnished'] = df['raw_text'].apply(is_furnished)

# Calculate metrics
df['price_per_m2'] = df['price'] / df['size']

# Geospatial features
print("Calculating geospatial features...")
df['dist_center'] = df['district'].apply(calculate_dist_center)
df['dist_ubahn'] = df['district'].apply(calculate_dist_ubahn)

# Create Fingerprint for tracking
print("Generating property fingerprints...")
df['fingerprint'] = df.apply(create_fingerprint, axis=1)

# Drop invalid rows
df = df.dropna(subset=['price', 'size', 'district'])

# Save
df.to_csv(clean_path, index=False)
print(f"Data cleaned and saved to: {clean_path}")
print(f"Valid rows: {len(df)}")