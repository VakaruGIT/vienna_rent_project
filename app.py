import streamlit as st
import pandas as pd
import pickle
import os
import streamlit.components.v1 as components

# --- 1. CONFIGURATION ---
st.set_page_config(
    page_title="Vienna Rent Intelligence",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. LOAD DATA & MODEL ---
@st.cache_data
def load_data():
    path = "data/vienna_rent_clean.csv"
    if os.path.exists(path):
        df = pd.read_csv(path)
        df['district'] = df['district'].astype(int)
        return df
    return None

@st.cache_resource
def load_model():
    paths = ["models/rent_price_model.pkl", "data/rent_price_model.pkl"]
    for path in paths:
        if os.path.exists(path):
            with open(path, "rb") as f:
                model_data = pickle.load(f)
                # Handle both old (just model) and new (dict with metadata) formats
                if isinstance(model_data, dict):
                    return model_data
                else:
                    # Old format: wrap in dict for compatibility
                    return {'model': model_data, 'features': None}
    return None

df = load_data()
model_data = load_model()
model = model_data['model'] if model_data else None
model_features = model_data['features'] if model_data else None

# --- 3. SIDEBAR CONTROLS ---
# District name mapping (postal codes to names)
DISTRICT_NAMES = {
    1010: "Innere Stadt", 1020: "Leopoldstadt", 1030: "Landstraße", 1040: "Wieden", 1050: "Margareten",
    1060: "Mariahilf", 1070: "Neubau", 1080: "Josefstadt", 1090: "Alsergrund", 1100: "Favoriten",
    1110: "Simmering", 1120: "Meidling", 1130: "Hietzing", 1140: "Penzing", 1150: "Rudolfsheim-Fünfhaus",
    1160: "Ottakring", 1170: "Hernals", 1180: "Währing", 1190: "Döbling", 1200: "Brigittenau",
    1210: "Floridsdorf", 1220: "Donaustadt", 1230: "Liesing"
}

with st.sidebar:
    st.header("Filters")
    
    if df is not None:
        # District filter with names
        districts = sorted(df['district'].unique())
        district_options = [f"{int(d)} ({DISTRICT_NAMES.get(int(d), 'Unknown')})" for d in districts]
        sel_dist_display = st.multiselect("Districts", district_options, default=[])
        sel_dist = [int(d.split()[0]) for d in sel_dist_display] if sel_dist_display else []
        
        # Price range filter
        min_p, max_p = int(df['price'].min()), int(df['price'].max())
        price_rng = st.slider("Price Range (€)", min_p, max_p, (500, 2500))
        
        # Rooms filter
        if 'rooms' in df.columns:
            min_r, max_r = int(df['rooms'].min()), int(df['rooms'].max())
            rooms_rng = st.slider("Rooms", min_r, max_r, (min_r, max_r))
        else:
            rooms_rng = None
        
        # Size filter
        if 'size' in df.columns:
            min_s, max_s = int(df['size'].min()), int(df['size'].max())
            size_rng = st.slider("Size (m²)", min_s, max_s, (min_s, max_s))
        else:
            size_rng = None
        
        # Boolean filters
        st.subheader("Features")
        if 'has_outdoor' in df.columns:
            outdoor_filter = st.checkbox("Has Outdoor Space", value=False)
        else:
            outdoor_filter = False
            
        if 'is_furnished' in df.columns:
            furnished_filter = st.checkbox("Furnished", value=False)
        else:
            furnished_filter = False
            
        if 'is_neubau' in df.columns:
            neubau_filter = st.checkbox("New Construction", value=False)
        else:
            neubau_filter = False
        
        # Apply Filters
        df_filtered = df.copy()
        
        if sel_dist:
            df_filtered = df_filtered[df_filtered['district'].isin(sel_dist)]
            
        df_filtered = df_filtered[df_filtered['price'].between(price_rng[0], price_rng[1])]
        
        if rooms_rng:
            df_filtered = df_filtered[df_filtered['rooms'].between(rooms_rng[0], rooms_rng[1])]
            
        if size_rng:
            df_filtered = df_filtered[df_filtered['size'].between(size_rng[0], size_rng[1])]
        
        if outdoor_filter:
            df_filtered = df_filtered[df_filtered['has_outdoor'] == True]
            
        if furnished_filter:
            df_filtered = df_filtered[df_filtered['is_furnished'] == True]
            
        if neubau_filter:
            df_filtered = df_filtered[df_filtered['is_neubau'] == True]
        
        st.divider()
        st.caption(f"Analyzing {len(df_filtered)} listings")
    else:
        st.error("Data missing")
        st.stop()

# --- 4. MAIN DASHBOARD ---
st.title("Vienna Rent Intelligence")
st.caption(f"Market Snapshot: {pd.to_datetime('now').strftime('%Y-%m-%d')}")

# Check if filtered dataset is empty
if df_filtered.empty:
    st.error("No listings match your current filter criteria. Please adjust the filters in the sidebar.")
    st.stop()

# KPI Row
col1, col2, col3, col4 = st.columns(4)
col1.metric("Active Listings", len(df_filtered), border=True)
col2.metric("Avg. Rent", f"€{df_filtered['price'].mean():,.0f}", border=True)
col3.metric("Avg. Price/m²", f"€{df_filtered['price_per_m2'].mean():.2f}", border=True)
col4.metric("Cheapest Found", f"€{df_filtered['price'].min():,.0f}", border=True)

# --- 5. TABS ---
# Reduced to just the two core features
tab1, tab2 = st.tabs(["Deal Radar", "Interactive Map"])

# --- TAB 1: DEAL RADAR (The Money Maker) ---
with tab1:
    st.subheader("Undervalued Opportunities")
    st.write("Listings where the Asking Price is significantly lower than the AI Predicted Value.")
    
    # Check if any listings match filters
    if df_filtered.empty:
        st.warning("No listings match your current filters. Try adjusting the criteria.")
    elif model:
        # Use features from model metadata, or fallback to basic features
        if model_features:
            req_cols = model_features
        else:
            # Fallback for old models without metadata
            req_cols = ['size', 'rooms', 'district', 'has_outdoor', 'is_neubau', 'is_furnished']
        
        if all(col in df_filtered.columns for col in req_cols):
            X = df_filtered[req_cols]
            df_filtered['predicted'] = model.predict(X)
            df_filtered['deal_score'] = df_filtered['price'] - df_filtered['predicted']
            
            # Sort by biggest savings (negative deal score)
            deals = df_filtered.sort_values('deal_score').head(10)
            
            if deals.empty:
                st.info("No listings match your filters.")
            
            for _, row in deals.iterrows():
                with st.container(border=True):
                    c1, c2, c3 = st.columns([3, 1, 1])
                    
                    with c1:
                        st.markdown(f"**{row['raw_text']}**")
                        st.text(f"District {row['district']} | {row['size']}m² | {row['rooms']} Rooms")
                        st.link_button("Open Listing", row['link'])
                    
                    with c2:
                        st.metric("Asking Price", f"€{row['price']:.0f}")
                    
                    with c3:
                        savings = abs(row['deal_score'])
                        st.metric("AI Estimated Value", f"€{row['predicted']:.0f}", delta=f"Save €{savings:.0f}")
        else:
            st.warning("Geospatial features missing. Please run the pipeline to generate them.")

# --- TAB 2: INTERACTIVE MAP ---
with tab2:
    st.subheader("Geospatial View")
    
    map_path = "data/vienna_rent_map.html"
    if os.path.exists(map_path):
        with open(map_path, 'r', encoding='utf-8') as f:
            map_html = f.read()
        components.html(map_html, height=600, scrolling=False)
    else:
        st.warning("Map file not found. It will be generated on the next pipeline run.")