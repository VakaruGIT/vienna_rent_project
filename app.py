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
                return pickle.load(f)
    return None

df = load_data()
model = load_model()

# --- 3. SIDEBAR CONTROLS ---
with st.sidebar:
    st.header("Filters")
    
    if df is not None:
        districts = sorted(df['district'].unique())
        # CHANGED: Default is empty (means ALL districts selected)
        sel_dist = st.multiselect("Select Districts", districts, default=[])
        
        min_p, max_p = int(df['price'].min()), int(df['price'].max())
        price_rng = st.slider("Price Range (€)", min_p, max_p, (500, 2500))
        
        # Filter Data
        if sel_dist:
            df_filtered = df[df['district'].isin(sel_dist)]
        else:
            df_filtered = df # Show all if none selected
            
        df_filtered = df_filtered[df_filtered['price'].between(price_rng[0], price_rng[1])]
        
        st.divider()
        st.caption(f"Analyzing {len(df_filtered)} listings")
    else:
        st.error("Data missing")
        st.stop()

# --- 4. MAIN DASHBOARD ---
st.title("Vienna Rent Intelligence")
st.caption(f"Market Snapshot: {pd.to_datetime('now').strftime('%Y-%m-%d')}")

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
    
    if model:
        req_cols = ['size', 'rooms', 'district', 'has_outdoor', 'is_neubau', 'is_furnished', 'dist_center', 'dist_ubahn']
        
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