import pandas as pd
import re # The "Regex" library - essential for scraping

# 1. LOAD THE RAW ORE
df = pd.read_csv("vienna_rent_full_scroll.csv")

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

# 2. APPLY THE REFINERY
print("Cleaning data...")

df['price'] = df['raw_text'].apply(extract_price)
df['size'] = df['raw_text'].apply(extract_size)
df['district'] = df['raw_text'].apply(extract_district)

# 3. CALCULATE METRICS (The "Insight")
# Create a price per m² column
df['price_per_m2'] = df['price'] / df['size']

# 4. INSPECT
print(df[['district', 'size', 'price', 'price_per_m2']])

# 5. SAVE
df.to_csv("vienna_rent_clean.csv", index=False)