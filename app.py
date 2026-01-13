import streamlit as st
import pandas as pd
import pickle
import os
import folium
from streamlit_folium import st_folium

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Vienna Rent AI",
    layout="wide"
)

# --- LOAD DATA ---
@st.cache_data
def load_data():
    path = "data/vienna_rent_clean.csv"
    if os.path.exists(path):
        return pd.read_csv(path)
    return None

@st.cache_resource
def load_model():
    # Try loading from the models folder first, then check data folder as backup
    paths = ["models/rent_price_model.pkl", "data/rent_price_model.pkl"]
    for path in paths:
        if os.path.exists(path):
            with open(path, "rb") as f:
                return pickle.load(f)
    return None

df = load_data()
model = load_model()

# --- HEADER ---
st.title("Vienna Rent Market Watch")
st.markdown("### AI-Powered Real Estate Analytics")

# --- CHECK DATA STATUS ---
if df is None:
    st.error("Data not found. The pipeline needs to run first.")
    st.stop()

# --- METRICS ROW ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Active Listings", len(df))
col2.metric("Avg Price / m2", f"{df['price_per_m2'].mean():.2f} Euro")
col3.metric("Cheapest District", f"{int(df.groupby('district')['price'].mean().idxmin())}")
col4.metric("Most Expensive District", f"{int(df.groupby('district')['price'].mean().idxmax())}")

# --- TABS LAYOUT ---
tab1, tab2, tab3 = st.tabs(["Price Predictor", "Market Heatmap", "Raw Data"])

# --- TAB 1: PREDICTOR ---
with tab1:
    st.subheader("Fair Rent Calculator")
    st.write("Enter apartment details to estimate the fair market rent.")
    
    if model:
        c1, c2, c3 = st.columns(3)
        with c1:
            size = st.number_input("Size (m2)", 20, 200, 60)
            rooms = st.number_input("Rooms", 1, 6, 2)
        with c2:
            # handle case where district column might be int or float
            districts = sorted(df['district'].unique())
            dist = st.selectbox("District", districts)
            neubau = st.checkbox("Neubau (New Building)")
        with c3:
            outdoor = st.checkbox("Balcony / Terrace")
            furnished = st.checkbox("Furnished")
        
        if st.button("Predict Fair Rent", type="primary"):
            # Get geospatial features for selected district
            dist_center = df[df['district'] == dist]['dist_center'].iloc[0] if 'dist_center' in df.columns else 0
            dist_ubahn = df[df['district'] == dist]['dist_ubahn'].iloc[0] if 'dist_ubahn' in df.columns else 0
            
            # Feature order must match training exactly: 
            # ['size', 'rooms', 'district', 'has_outdoor', 'is_neubau', 'is_furnished', 'dist_center', 'dist_ubahn']
            input_vector = [[size, rooms, dist, int(outdoor), int(neubau), int(furnished), dist_center, dist_ubahn]]
            prediction = model.predict(input_vector)[0]
            
            st.success(f"Estimated Fair Rent: **€{prediction:.0f}**")
            st.info(f"Typical range: €{prediction*0.9:.0f} - €{prediction*1.1:.0f}")
            
            # Show location insights
            if dist_center and dist_ubahn:
                col_a, col_b = st.columns(2)
                with col_a:
                    st.metric("Distance to Center", f"{dist_center:.1f} km", 
                             "🏛️ Stephansplatz")
                with col_b:
                    st.metric("Nearest U-Bahn", f"{dist_ubahn:.1f} km",
                             "🚇 Station")
    else:
        st.warning("Prediction Model not found. Pipeline must run successfully first.")

# --- TAB 2: HEATMAP ---
with tab2:
    st.subheader("Price Intensity Map")
    
    map_file = "data/vienna_rent_map.html"
    if os.path.exists(map_file):
        with open(map_file, "r", encoding="utf-8") as f:
            map_html = f.read()
        st.components.v1.html(map_html, height=600)
    else:
        st.warning("Map file not generated yet.")

# --- TAB 3: DATA ---
with tab3:
    st.subheader("Latest Listings")
    st.dataframe(df[['raw_text', 'price', 'size', 'district', 'link']].sort_values('price'))

# --- SIDEBAR INFO ---
st.sidebar.markdown("---")
st.sidebar.caption("Last Updated: " + pd.to_datetime("now").strftime("%Y-%m-%d"))