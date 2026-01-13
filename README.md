# Vienna Rent Analysis Project

Automated data pipeline for scraping, analyzing, and visualizing rental apartment prices across Vienna's 23 districts.

## Overview

This project collects rental listings from willhaben.at and transforms raw data into actionable market insights through feature extraction, geospatial analysis, historical tracking, and machine learning price predictions.

## Features

- Web scraping with anti-detection measures and checkpoint recovery
- Regex-based feature extraction optimized for Austrian terminology
- Geospatial engineering with distance calculations to city center and U-Bahn stations
- Historical tracking system with duplicate detection via property fingerprinting
- Interactive choropleth map with district statistics and individual listing markers
- Random Forest price prediction model with feature importance analysis
- Streamlit dashboard with deal detection and market insights
- Modular pipeline orchestrator for automated daily execution

## Project Structure

```
vienna_rent_project/
├── data/
│   ├── vienna_rent_raw.csv          # Daily scrape output (temp)
│   ├── vienna_rent_clean.csv        # Processed data with features
│   ├── vienna_rent_history.csv      # Historical database (append-only)
│   ├── vienna_rent_map.html         # Interactive Folium map
│   ├── vienna_geo_cache.json        # Cached district boundaries
│   └── scrape_checkpoint.csv        # Crash recovery checkpoint
├── scripts/
│   ├── run_pipeline.py              # Master orchestrator
│   ├── scraper.py                   # Web scraping automation
│   ├── cleaner.py                   # Feature extraction and geospatial calculations
│   ├── tracker.py                   # Historical database management
│   ├── mapper.py                    # Interactive map generation
│   └── train_model.py               # ML model training
├── models/
│   └── rent_price_model.pkl         # Trained Random Forest model
├── archive/
│   ├── scraper_deep.py              # Detail page scraper (GPS, transport, energy)
│   ├── track_changes.py             # Advanced lifecycle tracking
│   ├── test_predictions.py          # Model testing script
│   └── simulate_tomorrow.py         # Data simulation for testing
├── .github/
│   └── workflows/
│       └── daily_scrape.yml         # GitHub Actions automation
├── app.py                           # Streamlit dashboard
├── requirements.txt
├── .gitignore
└── README.md
```

## Installation

### Prerequisites

- Python 3.8+
- Google Chrome browser
- ChromeDriver compatible with installed Chrome version

### Setup

1. Clone repository and navigate to project directory

2. Create virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Automated Pipeline (Recommended)

Run all steps sequentially:
```bash
python scripts/run_pipeline.py
```

Executes in order:
1. Scraping
2. Cleaning
3. Historical tracking
4. Map generation
5. Model training

### Manual Execution

Run individual components:

```bash
# Data collection
python scripts/scraper.py

# Feature extraction
python scripts/cleaner.py

# Update history
python scripts/tracker.py

# Generate map
python scripts/mapper.py

# Train model
python scripts/train_model.py
```

### Interactive Dashboard

Launch Streamlit app:
```bash
streamlit run app.py
```

Features:
- Price calculator with ML predictions
- Deal radar showing undervalued listings
- Interactive map with district filtering
- Market statistics and insights

## Configuration

### Scraper Settings (scripts/scraper.py)

```python
PAGES_TO_SCRAPE = 10      # Number of pages to scrape
HEADLESS = True           # Run without browser window
CHECKPOINT_EVERY = 3      # Save progress every N pages
```

### Model Features (scripts/train_model.py)

```python
CANDIDATE_FEATURES = [
    'size', 'rooms', 'district', 'has_outdoor', 
    'is_neubau', 'is_furnished', 'dist_center', 'dist_ubahn'
]
```

## Data Schema

### Raw Data (vienna_rent_raw.csv)

| Column | Type | Description |
|--------|------|-------------|
| raw_text | str | Original listing text |
| link | str | Listing URL |
| page_found | int | Page number |
| scrape_timestamp | datetime | Collection timestamp |

### Cleaned Data (vienna_rent_clean.csv)

| Column | Type | Description |
|--------|------|-------------|
| price | float | Monthly rent (EUR) |
| size | int | Area (m²) |
| rooms | int | Number of rooms |
| district | int | Postal code (1010-1230) |
| has_outdoor | int | Balcony/terrace/garden (0/1) |
| is_neubau | int | New building (0/1) |
| is_furnished | int | Furnished (0/1) |
| price_per_m2 | float | Price per square meter |
| dist_center | float | Distance to Stephansplatz (km) |
| dist_ubahn | float | Distance to nearest U-Bahn (km) |
| fingerprint | str | Unique property identifier |

### Historical Data (vienna_rent_history.csv)

Same schema as cleaned data plus:
- `snapshot_date`: Scrape date (YYYY-MM-DD)

Critical for:
- Time-series analysis
- ML model training with more data
- Trend detection and seasonal patterns
- Market velocity calculations

## Technical Implementation

### Web Scraping Strategy

- Target: willhaben.at Vienna rental section
- Method: Selenium WebDriver with Chrome
- Anti-detection: randomized delays (0.3-3.0s), human-like scrolling, realistic user agent
- Resilience: retry logic, checkpoint saves every 3 pages, graceful error handling
- Performance: approximately 6-7 seconds per page
- Deduplication: merges with existing data to avoid re-scraping

### Feature Engineering

Regex patterns for Austrian German:
- Rooms: `(\d+)\s*(?:Zimmer|Zi)` 
- District: `(1\d{3})` (postal codes)
- Size: `(\d+)\s*m²`
- Price: `€\s*([\d.,]+)` with German number format handling

Geospatial features via Haversine formula:
- Distance from district centers to Stephansplatz
- Distance to nearest of 10 major U-Bahn stations
- Improves model R² by approximately 5%

Property fingerprinting:
- MD5 hash of district, size, rooms, price
- Enables re-upload detection (same property, different listing)
- Filters duplicate properties with different URLs

### Mapping System

- Data source: Open Government Data Vienna (ogdwien:BEZIRKSGRENZEOGD)
- Library: Folium with plugins (Fullscreen, MiniMap, MeasureControl)
- Choropleth: red-yellow-green reversed scale
- Price bins: [10, 15, 18, 21, 25, 30, 40] EUR/m²
- Cached GeoJSON to avoid repeated API calls
- Three overlay layers: heatmap, district markers, individual listings

### Machine Learning

Model: Random Forest Regressor
- Features: 8 (including geospatial)
- Training set filtering: removes top 1% price outliers
- 80/20 train-test split
- Performance metrics: R² score, Mean Absolute Error
- Feature importance ranking

Typical performance:
- R² Score: 0.75-0.85
- MAE: ±€150-200
- Top feature: apartment size (40%+ importance)

### Historical Tracking

Intelligent duplicate detection:
- Property fingerprints identify physical properties
- Link comparison detects re-uploads
- Alerts for truly new listings vs re-posted properties
- Maintains append-only database for trend analysis

## Market Insights

Based on dataset analysis (300+ listings):

**Price Drivers:**
- Outdoor space: +18.9% premium per m²
- Furnished apartments: +46.2% premium
- District location: inner districts €32/m², outer districts €18-20/m²

**Market Overview:**
- Average rent: €22.56/m²
- Most expensive: District 1010 (Innere Stadt) at €32.26/m²
- Most affordable: Districts 1100, 1210, 1220 at €18-20/m²
- Most common: 2-room apartments (43% of listings)

**Feature Coverage:**
- 69% include outdoor space
- 15.3% are new buildings
- 3% are furnished
- Geographic features: 100% coverage via district mapping

## Automation

### GitHub Actions Workflow

Daily automated execution:

```yaml
name: Daily Vienna Rent Pipeline
on:
  schedule:
    - cron: '0 6 * * *'
  workflow_dispatch:

jobs:
  scrape:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - run: pip install -r requirements.txt
      - run: python scripts/run_pipeline.py
      - run: git add data/ && git commit -m "Daily update" && git push
```

Requires:
- Headless Chrome setup in Ubuntu
- Repository write permissions
- Selenium configuration for GitHub Actions environment

## Advanced Features (Archive)

### Deep Scraper (archive/scraper_deep.py)

Clicks into detail pages for enhanced data extraction:
- GPS coordinates for precise mapping
- Transportation mentions (U-Bahn lines, walking times)
- Building features (elevator, parking, year built)
- Financial details (deposit, Betriebskosten, heating)
- Energy ratings (HWB, efficiency class)
- Photo count as quality indicator
- Availability dates

Trade-off: 10x slower (5 seconds per listing) but 5x more features.

Use cases:
- Advanced ML model training
- Geospatial analysis requiring exact coordinates
- Commercial product development

### Change Tracker (archive/track_changes.py)

Advanced lifecycle tracking system:
- New vs existing listing detection
- Price change monitoring with percentage calculations
- Removed listing archive (likely rented)
- Days on market calculation
- Market velocity analysis (fast vs slow rentals)
- Price trend detection (market heating/cooling)

Database structure:
- `vienna_rent_active.csv`: current snapshot
- `vienna_rent_removed.csv`: historical removals
- `vienna_rent_history.csv`: complete timeline

## Dependencies

Core libraries:
- selenium: web automation
- pandas: data manipulation
- folium: interactive mapping
- scikit-learn: machine learning
- streamlit: dashboard interface
- requests: HTTP requests

See requirements.txt for complete list with versions.

## Future Enhancements

Potential improvements:
- Email alerts for new matching listings
- Time-series forecasting (ARIMA, Prophet)
- Multi-city expansion (Graz, Salzburg, Linz)
- Energy efficiency rating analysis
- Detailed transportation accessibility scores
- Price anomaly detection
- Integration with property APIs

## Legal Notice

This project is for educational and personal use only. Users must respect willhaben.at's terms of service and robots.txt guidelines. The authors assume no responsibility for misuse.

## License

MIT License

## Author

Data engineering portfolio project demonstrating end-to-end pipeline development, geospatial analysis, and machine learning integration.

Last updated: January 2026