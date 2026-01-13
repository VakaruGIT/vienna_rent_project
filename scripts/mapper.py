import pandas as pd
import folium
from folium import plugins
import requests
import json
import os
from datetime import datetime

# 1. LOAD YOUR DATA
script_dir = os.path.dirname(os.path.abspath(__file__))
data_path = os.path.join(script_dir, "..", "data", "vienna_rent_clean.csv")

print("Loading data...")
df = pd.read_csv(data_path)

# Remove rows with missing critical data
df = df.dropna(subset=['district', 'price_per_m2', 'price'])

# 2. DATA PREPARATION (Enhanced with robust statistics)
district_stats = df.groupby('district').agg({
    'price_per_m2': ['mean', 'median', 'std', 'min', 'max'],
    'raw_text': 'count',
    'price': ['min', 'median']
}).reset_index()

# Flatten column names
district_stats.columns = ['district', 'avg_sqm_price', 'median_sqm_price', 'std_sqm_price', 
                          'min_sqm_price', 'max_sqm_price', 'ad_count', 'cheapest_rent', 'median_rent']

# Filter out districts with too few listings (unreliable data)
MIN_LISTINGS = 3
district_stats = district_stats[district_stats['ad_count'] >= MIN_LISTINGS]
print(f"Districts with {MIN_LISTINGS}+ listings: {len(district_stats)}")

# THE TRANSLATION TRICK
def get_district_id(zip_code):
    return int(str(zip_code)[1:3])

district_stats['district_id'] = district_stats['district'].apply(get_district_id)

print("District Stats (Top 5):")
print(district_stats.head())

# --- DISTRICT NAMES (German + Postal Codes) ---
DISTRICT_NAMES = {
    1010: "Innere Stadt", 1020: "Leopoldstadt", 1030: "Landstraße",
    1040: "Wieden", 1050: "Margareten", 1060: "Mariahilf",
    1070: "Neubau", 1080: "Josefstadt", 1090: "Alsergrund",
    1100: "Favoriten", 1110: "Simmering", 1120: "Meidling",
    1130: "Hietzing", 1140: "Penzing", 1150: "Rudolfsheim-Fünfhaus",
    1160: "Ottakring", 1170: "Hernals", 1180: "Währing",
    1190: "Döbling", 1200: "Brigittenau", 1210: "Floridsdorf",
    1220: "Donaustadt", 1230: "Liesing"
}

# --- COORDINATES FOR MARKERS ---
DISTRICT_CENTERS = {
    1010: [48.208174, 16.373819], 1020: [48.216667, 16.416667], 1030: [48.198611, 16.395833],
    1040: [48.191667, 16.366667], 1050: [48.188889, 16.355556], 1060: [48.195000, 16.350000],
    1070: [48.201389, 16.348611], 1080: [48.211111, 16.347222], 1090: [48.223611, 16.358333],
    1100: [48.156111, 16.381389], 1110: [48.169167, 16.438333], 1120: [48.170000, 16.326389],
    1130: [48.179167, 16.275278], 1140: [48.208611, 16.262500], 1150: [48.196667, 16.325556],
    1160: [48.213333, 16.305556], 1170: [48.228889, 16.305556], 1180: [48.231944, 16.331667],
    1190: [48.256111, 16.336111], 1200: [48.238889, 16.375556], 1210: [48.272778, 16.416944],
    1220: [48.233333, 16.466667], 1230: [48.140278, 16.291111]
}

# 3. GET THE MAP SHAPES (with caching and error handling)
cache_file = os.path.join(script_dir, "..", "data", "vienna_geo_cache.json")
geo_url = "https://data.wien.gv.at/daten/geo?service=WFS&request=GetFeature&version=1.1.0&typeName=ogdwien:BEZIRKSGRENZEOGD&srsName=EPSG:4326&outputFormat=json"

# Try to load from cache first
if os.path.exists(cache_file):
    print("Loading Vienna map from cache...")
    with open(cache_file, 'r', encoding='utf-8') as f:
        vienna_geo = json.load(f)
else:
    print("Downloading Vienna map data...")
    try:
        response = requests.get(geo_url, timeout=10)
        response.raise_for_status()
        vienna_geo = response.json()
        # Save to cache
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(vienna_geo, f)
        print("Map data cached successfully")
    except requests.exceptions.RequestException as e:
        print(f"Error downloading map: {e}")
        print("Cannot proceed without map data.")
        exit(1)

# --- MERGE DATA INTO GEOJSON (Enhanced with district names and all statistics) ---
for feature in vienna_geo['features']:
    bez_id = int(feature['properties']['BEZNR'])
    row = district_stats[district_stats['district_id'] == bez_id]
    
    # Get district info
    postal_code = 1000 + (bez_id * 10)
    district_name = DISTRICT_NAMES.get(postal_code, f"District {bez_id}")
    
    if not row.empty:
        r = row.iloc[0]
        feature['properties']['district_name'] = district_name
        feature['properties']['postal_code'] = postal_code
        feature['properties']['avg_price'] = round(r['avg_sqm_price'], 2)
        feature['properties']['median_price'] = round(r['median_sqm_price'], 2)
        feature['properties']['price_range'] = f"{r['min_sqm_price']:.1f} - {r['max_sqm_price']:.1f}"
        feature['properties']['count'] = int(r['ad_count'])
        feature['properties']['cheapest'] = round(r['cheapest_rent'], 0)
        feature['properties']['median_rent'] = round(r['median_rent'], 0)
    else:
        feature['properties']['district_name'] = district_name
        feature['properties']['postal_code'] = postal_code
        feature['properties']['avg_price'] = "No Data"
        feature['properties']['median_price'] = "No Data"
        feature['properties']['price_range'] = "No Data"
        feature['properties']['count'] = 0
        feature['properties']['cheapest'] = "N/A"
        feature['properties']['median_rent'] = "N/A"

# 4. BUILD THE INTERACTIVE MAP (Enhanced with controls)
m = folium.Map(
    location=[48.2082, 16.3738], 
    zoom_start=11, 
    tiles="cartodbpositron",
    control_scale=True
)

# Add Font Awesome CSS for professional icons
fontawesome_css = """
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
"""
m.get_root().html.add_child(folium.Element(fontawesome_css))

# Add alternative tile layers
folium.TileLayer('OpenStreetMap', name='Street Map').add_to(m)

# LAYER 1: HEATMAP (with better color bins)
choropleth = folium.Choropleth(
    geo_data=vienna_geo,
    name="District Heatmap",
    data=district_stats,
    columns=["district_id", "avg_sqm_price"],
    key_on="feature.properties.BEZNR",
    fill_color="RdYlGn_r",  # Red (expensive) to Green (cheap)
    fill_opacity=0.7,
    line_opacity=0.5,
    line_color='black',
    legend_name="Avg Rent (€/m²)",
    nan_fill_color="#cccccc",
    highlight=True,
    bins=[10, 15, 18, 21, 25, 30, 40]  # Custom bins for better visualization
).add_to(m)

# ENHANCED TOOLTIP with district names
folium.GeoJsonTooltip(
    fields=['district_name', 'postal_code', 'avg_price', 'median_price', 'count'],
    aliases=['District:', 'Postal Code:', 'Avg €/m²:', 'Median €/m²:', 'Listings:'],
    style="background-color: white; color: #333333; font-family: arial; font-size: 13px; padding: 12px; border: 2px solid #333;"
).add_to(choropleth.geojson)

# ENHANCED POPUP with district listings on click
def create_district_popup(district_code, district_name):
    """Generate HTML popup showing top listings in this district"""
    district_listings = df[df['district'] == district_code].copy()
    
    if district_listings.empty:
        return f"<h4>{district_name} ({int(district_code)})</h4><p>No listings found</p>"
    
    # Calculate value score (lower price per m² = better value)
    district_listings['value_score'] = 1 / district_listings['price_per_m2']
    district_listings = district_listings.sort_values('value_score', ascending=False).head(10)
    
    # Build HTML table
    html = f"""
    <div style="font-family: Arial; font-size: 12px; max-width: 450px; max-height: 400px; overflow-y: auto;">
        <h3 style="margin: 0 0 10px 0; color: #2c3e50;">{district_name} ({int(district_code)})</h3>
        <p style="margin: 5px 0; color: #666;"><b>Top 10 Best Value Listings:</b></p>
        <table style="width: 100%; border-collapse: collapse; font-size: 11px;">
            <tr style="background: #34495e; color: white;">
                <th style="padding: 6px; text-align: left;">€</th>
                <th style="padding: 6px;">m²</th>
                <th style="padding: 6px;">Rooms</th>
                <th style="padding: 6px;">€/m²</th>
                <th style="padding: 6px;">Features</th>
                <th style="padding: 6px;">Link</th>
            </tr>
    """
    
    for idx, row in district_listings.iterrows():
        # Features icons (Font Awesome)
        features = []
        if row.get('has_outdoor', 0) == 1:
            features.append('<i class="fas fa-tree" style="color: #27ae60;" title="Outdoor Space"></i>')
        if row.get('is_furnished', 0) == 1:
            features.append('<i class="fas fa-couch" style="color: #e67e22;" title="Furnished"></i>')
        if row.get('is_neubau', 0) == 1:
            features.append('<i class="fas fa-building" style="color: #3498db;" title="New Building"></i>')
        features_str = ' '.join(features) if features else '-'
        
        rooms = int(row['rooms']) if pd.notna(row['rooms']) else '?'
        size = int(row['size']) if pd.notna(row['size']) else '?'
        
        html += f"""
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 6px;"><b>€{int(row['price'])}</b></td>
                <td style="padding: 6px; text-align: center;">{size}</td>
                <td style="padding: 6px; text-align: center;">{rooms}</td>
                <td style="padding: 6px; text-align: center;">€{row['price_per_m2']:.1f}</td>
                <td style="padding: 6px; text-align: center;">{features_str}</td>
                <td style="padding: 6px; text-align: center;"><a href="{row['link']}" target="_blank" title="View on willhaben.at"><i class="fas fa-external-link-alt" style="color: #3498db;"></i></a></td>
            </tr>
        """
    
    html += """
        </table>
        <p style="margin: 10px 0 0 0; font-size: 10px; color: #888;">
            <i class="fas fa-tree" style="color: #27ae60;"></i>=Outdoor 
            <i class="fas fa-couch" style="color: #e67e22;"></i>=Furnished 
            <i class="fas fa-building" style="color: #3498db;"></i>=Neubau | 
            Click <i class="fas fa-external-link-alt"></i> to view listing
        </p>
    </div>
    """
    return html

# Create invisible popup layer (grouped so it doesn't clutter layer control)
popup_group = folium.FeatureGroup(name="District Popups", show=True, overlay=True, control=False)

# Apply popups to districts
for feature in vienna_geo['features']:
    bez_id = int(feature['properties']['BEZNR'])
    postal_code = 1000 + (bez_id * 10)
    district_name = feature['properties'].get('district_name', f"District {bez_id}")
    
    popup_html = create_district_popup(postal_code, district_name)
    
    # Add invisible clickable layer for popups
    folium.GeoJson(
        feature,
        style_function=lambda x: {'fillOpacity': 0, 'weight': 0, 'opacity': 0},  # Completely invisible
        popup=folium.Popup(popup_html, max_width=500)
    ).add_to(popup_group)

popup_group.add_to(m)

# FEATURE 2: DISTRICT SUMMARY MARKERS (with names)
district_marker_group = folium.FeatureGroup(name="District Info", show=True)

for _, row in district_stats.iterrows():
    dist_code = int(row['district'])
    if dist_code in DISTRICT_CENTERS:
        district_name = DISTRICT_NAMES.get(dist_code, f"District {dist_code}")
        
        # Color code by price: green=cheap, yellow=medium, red=expensive
        avg_price = row['avg_sqm_price']
        if avg_price < 18:
            color, icon_color = 'green', 'white'
        elif avg_price < 25:
            color, icon_color = 'orange', 'white'
        else:
            color, icon_color = 'red', 'white'
        
        popup_html = f"""
        <div style="font-family: Arial; font-size: 13px; min-width: 220px;">
            <h4 style="margin: 0 0 10px 0; color: #333;">{district_name}</h4>
            <p style="margin: 0 0 8px 0; color: #666; font-size: 11px;">Postal Code: {dist_code}</p>
            <table style="width: 100%; border-collapse: collapse;">
                <tr><td><b>Avg €/m²:</b></td><td>€{row['avg_sqm_price']:.2f}</td></tr>
                <tr><td><b>Median €/m²:</b></td><td>€{row['median_sqm_price']:.2f}</td></tr>
                <tr><td><b>Cheapest:</b></td><td>€{row['cheapest_rent']:.0f}</td></tr>
                <tr><td><b>Median Rent:</b></td><td>€{row['median_rent']:.0f}</td></tr>
                <tr><td><b>Listings:</b></td><td>{row['ad_count']}</td></tr>
            </table>
        </div>
        """
        
        folium.Marker(
            location=DISTRICT_CENTERS[dist_code],
            popup=folium.Popup(popup_html, max_width=280),
            tooltip=f"{district_name}: €{row['avg_sqm_price']:.1f}/m²",
            icon=folium.Icon(color=color, icon="info-sign", prefix='glyphicon', icon_color=icon_color)
        ).add_to(district_marker_group)

district_marker_group.add_to(m)

# FEATURE 3: INDIVIDUAL LISTING MARKERS (NEW!)
listings_group = folium.FeatureGroup(name="All Apartments", show=True)

# Calculate "value score" for all listings
df['value_score'] = df.apply(lambda x: (
    (1 / x['price_per_m2']) * 100 +  # Lower price per m² is better
    (10 if x.get('has_outdoor', 0) == 1 else 0) +  # Outdoor bonus
    (5 if x.get('is_furnished', 0) == 1 else 0)  # Furnished bonus
), axis=1)

# Show top 100 best value listings
top_listings = df.nlargest(100, 'value_score')

for idx, row in top_listings.iterrows():
    dist_code = int(row['district']) if pd.notna(row['district']) else 1010
    
    # Use approximate location (add small random offset from district center)
    import random
    if dist_code in DISTRICT_CENTERS:
        base_loc = DISTRICT_CENTERS[dist_code]
        # Random offset ±0.01 degrees (~1km)
        lat = base_loc[0] + random.uniform(-0.01, 0.01)
        lon = base_loc[1] + random.uniform(-0.01, 0.01)
    else:
        continue
    
    # Color by value score
    if row['value_score'] > 70:
        marker_color = 'green'
    elif row['value_score'] > 50:
        marker_color = 'lightgreen'
    else:
        marker_color = 'orange'
    
    # Build feature icons (Font Awesome)
    features = []
    if row.get('has_outdoor', 0) == 1:
        features.append('<i class="fas fa-tree" style="color: #27ae60;"></i> Outdoor Space')
    if row.get('is_furnished', 0) == 1:
        features.append('<i class="fas fa-couch" style="color: #e67e22;"></i> Furnished')
    if row.get('is_neubau', 0) == 1:
        features.append('<i class="fas fa-building" style="color: #3498db;"></i> New Building')
    features_text = '<br>'.join(features) if features else '<span style="color: #999;">No special features</span>'
    
    rooms = int(row['rooms']) if pd.notna(row['rooms']) else '?'
    size = int(row['size']) if pd.notna(row['size']) else '?'
    
    popup_html = f"""
    <div style="font-family: Arial; font-size: 12px; min-width: 200px;">
        <h4 style="margin: 0 0 8px 0; color: #2c3e50;">€{int(row['price'])} / month</h4>
        <table style="width: 100%; font-size: 11px;">
            <tr><td><b>Size:</b></td><td>{size} m²</td></tr>
            <tr><td><b>Rooms:</b></td><td>{rooms}</td></tr>
            <tr><td><b>Price/m²:</b></td><td>€{row['price_per_m2']:.2f}</td></tr>
            <tr><td><b>District:</b></td><td>{DISTRICT_NAMES.get(dist_code, dist_code)}</td></tr>
        </table>
        <p style="margin: 8px 0; font-size: 11px;">{features_text}</p>
        <a href="{row['link']}" target="_blank" style="display: inline-block; background: #3498db; color: white; padding: 6px 12px; text-decoration: none; border-radius: 3px; margin-top: 5px;">View Listing →</a>
    </div>
    """
    
    folium.CircleMarker(
        location=[lat, lon],
        radius=6,
        popup=folium.Popup(popup_html, max_width=250),
        tooltip=f"€{int(row['price'])} | {rooms}R | {size}m²",
        color=marker_color,
        fill=True,
        fillColor=marker_color,
        fillOpacity=0.7,
        weight=2
    ).add_to(listings_group)

listings_group.add_to(m)

# Add advanced controls
plugins.Fullscreen(position='topright').add_to(m)
plugins.MiniMap(toggle_display=True, position='bottomright').add_to(m)
plugins.MeasureControl(position='topleft', primary_length_unit='meters').add_to(m)

# Layer control (collapsed by default for cleaner look)
folium.LayerControl(position='topright', collapsed=True).add_to(m)

# 6. SAVE
output_path = os.path.join(script_dir, "..", "data", "vienna_rent_map.html")
m.save(output_path)
print(f"\nSuccess! Map saved to '{output_path}'")
