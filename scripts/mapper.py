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

# --- MERGE DATA INTO GEOJSON (Enhanced with all statistics) ---
for feature in vienna_geo['features']:
    bez_id = int(feature['properties']['BEZNR'])
    row = district_stats[district_stats['district_id'] == bez_id]
    
    if not row.empty:
        r = row.iloc[0]
        feature['properties']['avg_price'] = round(r['avg_sqm_price'], 2)
        feature['properties']['median_price'] = round(r['median_sqm_price'], 2)
        feature['properties']['price_range'] = f"{r['min_sqm_price']:.1f} - {r['max_sqm_price']:.1f}"
        feature['properties']['count'] = int(r['ad_count'])
        feature['properties']['cheapest'] = round(r['cheapest_rent'], 0)
        feature['properties']['median_rent'] = round(r['median_rent'], 0)
    else:
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

# Add alternative tile layers
folium.TileLayer('OpenStreetMap', name='Street Map').add_to(m)

# LAYER 1: HEATMAP (with better color bins)
choropleth = folium.Choropleth(
    geo_data=vienna_geo,
    name="Rent Price Heatmap",
    data=district_stats,
    columns=["district_id", "avg_sqm_price"],
    key_on="feature.properties.BEZNR",
    fill_color="RdYlGn_r",  # Red (expensive) to Green (cheap)
    fill_opacity=0.7,
    line_opacity=0.5,
    line_color='black',
    legend_name="Average Rent (€/m²)",
    nan_fill_color="#cccccc",
    highlight=True,
    bins=[10, 15, 18, 21, 25, 30, 40]  # Custom bins for better visualization
).add_to(m)

# ENHANCED TOOLTIP with all statistics
folium.GeoJsonTooltip(
    fields=['BEZ', 'avg_price', 'median_price', 'price_range', 'count'],
    aliases=['District:', 'Avg €/m²:', 'Median €/m²:', 'Range €/m²:', 'Listings:'],
    style="background-color: white; color: #333333; font-family: arial; font-size: 13px; padding: 12px; border: 2px solid #333;"
).add_to(choropleth.geojson)

# ENHANCED POPUP with detailed info on click
folium.GeoJsonPopup(
    fields=['BEZ', 'avg_price', 'median_price', 'cheapest', 'median_rent', 'count'],
    aliases=['<b>District</b>', 'Avg Price/m²', 'Median Price/m²', 'Cheapest Total Rent', 'Median Total Rent', 'Listings Found'],
    style="background-color: #f0f0f0;",
    labels=True
).add_to(choropleth.geojson)

# FEATURE 2: BEST DEAL MARKERS (Improved with better info)
marker_group = folium.FeatureGroup(name="District Markers", show=True)

for _, row in district_stats.iterrows():
    dist_code = int(row['district'])
    if dist_code in DISTRICT_CENTERS:
        # Color code by price: green=cheap, yellow=medium, red=expensive
        avg_price = row['avg_sqm_price']
        if avg_price < 18:
            color, icon_color = 'green', 'white'
        elif avg_price < 25:
            color, icon_color = 'orange', 'white'
        else:
            color, icon_color = 'red', 'white'
        
        popup_html = f"""
        <div style="font-family: Arial; font-size: 13px; min-width: 200px;">
            <h4 style="margin: 0 0 10px 0; color: #333;">District {dist_code}</h4>
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
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=f"District {dist_code}: €{row['avg_sqm_price']:.1f}/m²",
            icon=folium.Icon(color=color, icon="home", prefix='glyphicon', icon_color=icon_color)
        ).add_to(marker_group)

marker_group.add_to(m)

# Add advanced controls
plugins.Fullscreen(position='topright').add_to(m)
plugins.MiniMap(toggle_display=True, position='bottomright').add_to(m)
plugins.MeasureControl(position='topleft', primary_length_unit='meters').add_to(m)

# Add statistics summary box
stats_html = f"""
<div style="position: fixed; top: 10px; left: 60px; width: 280px; background-color: white; 
     border: 2px solid grey; z-index: 9999; padding: 15px; border-radius: 5px; box-shadow: 3px 3px 10px rgba(0,0,0,0.3);">
    <h4 style="margin: 0 0 10px 0;">Vienna Rent Analysis</h4>
    <table style="width: 100%; font-size: 12px;">
        <tr><td><b>Total Listings:</b></td><td>{len(df)}</td></tr>
        <tr><td><b>Districts Covered:</b></td><td>{len(district_stats)}</td></tr>
        <tr><td><b>Avg Price/m²:</b></td><td>€{df['price_per_m2'].mean():.2f}</td></tr>
        <tr><td><b>Median Price/m²:</b></td><td>€{df['price_per_m2'].median():.2f}</td></tr>
        <tr><td><b>Cheapest District:</b></td><td>{district_stats.loc[district_stats['avg_sqm_price'].idxmin(), 'district']:.0f} (€{district_stats['avg_sqm_price'].min():.1f}/m²)</td></tr>
        <tr><td><b>Most Expensive:</b></td><td>{district_stats.loc[district_stats['avg_sqm_price'].idxmax(), 'district']:.0f} (€{district_stats['avg_sqm_price'].max():.1f}/m²)</td></tr>
    </table>
    <p style="font-size: 10px; margin: 10px 0 0 0; color: #666;">Data scraped: {datetime.now().strftime('%Y-%m-%d')}</p>
</div>
"""
m.get_root().html.add_child(folium.Element(stats_html))

# Layer control (must be last)
folium.LayerControl(position='topright', collapsed=False).add_to(m)

# 6. SAVE
output_path = os.path.join(script_dir, "..", "data", "vienna_rent_map.html")
m.save(output_path)
print(f"\nSuccess! Map saved to '{output_path}'")
