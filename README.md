# Vienna Rent Analysis Project

A comprehensive data pipeline for scraping, analyzing, and visualizing rental apartment prices across Vienna's 23 districts.

## Overview

This project automates the collection and analysis of rental listings from willhaben.at, providing insights into Vienna's rental market through data extraction, feature engineering, statistical analysis, and interactive mapping.

## Features

- **Web Scraping**: Automated collection of rental listings with anti-detection measures
- **Data Cleaning**: Regex-based extraction of structured features from raw text
- **Feature Engineering**: 13+ extracted features including rooms, outdoor space, building type, floor level
- **Statistical Analysis**: Price comparisons, premium calculations, market insights
- **Interactive Mapping**: Color-coded heatmap visualization with district-level statistics

## Project Structure

```
vienna_rent_project/
├── data/
│   ├── vienna_rent.csv              # Raw scraped data
│   ├── vienna_rent_clean.csv        # Cleaned and processed data
│   ├── vienna_rent_map.html         # Interactive map visualization
│   └── vienna_geo_cache.json        # Cached Vienna district boundaries
├── scripts/
│   ├── scraper.py                   # Web scraping script
│   ├── cleaner.py                   # Data cleaning and feature extraction
│   └── mapper.py                    # Map generation
├── requirements.txt                 # Python dependencies
└── README.md
```

## Installation

### Prerequisites

- Python 3.8+
- Google Chrome browser
- ChromeDriver (compatible with your Chrome version)

### Setup

1. Clone the repository:
```bash
cd vienna_rent_project
```

2. Create and activate virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On macOS/Linux
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### 1. Scrape Rental Listings

```bash
python scripts/scraper.py
```

**Features:**
- Scrapes 10 pages by default (configurable via `PAGES_TO_SCRAPE`)
- Runs in headless mode for faster execution
- Deduplicates listings automatically
- Saves checkpoints every 3 pages for crash recovery
- Merges with existing data to build historical dataset

**Configuration:**
```python
PAGES_TO_SCRAPE = 10    # Number of pages to scrape
HEADLESS = True          # Run without browser window
CHECKPOINT_EVERY = 3     # Save progress frequency
```

**Output:** `data/vienna_rent.csv` (raw data with ~16 columns)

### 2. Clean and Extract Features

```bash
python scripts/cleaner.py
```

**Extracted Features:**
- Basic: price, size (m²), district (postal code)
- Rooms: number of rooms/Zimmer
- Outdoor: balcony, terrace, loggia, garden
- Building type: Neubau (new) vs Altbau (old)
- Floor level: ground floor, upper floors
- Lease type: temporary (befristet) vs permanent
- Furnishing: furnished (möbliert) vs unfurnished

**Output:** `data/vienna_rent_clean.csv` with statistical insights printed to console

### 3. Generate Interactive Map

```bash
python scripts/mapper.py
```

**Features:**
- Color-coded choropleth by average rent per m²
- District-level statistics (mean, median, range)
- Interactive markers with detailed popup information
- Toggle layers (heatmap, markers, base maps)
- Fullscreen mode, minimap, measurement tool
- Summary statistics panel

**Output:** `data/vienna_rent_map.html` (open in browser)

## Data Schema

### Raw Data (vienna_rent.csv)

| Column | Type | Description |
|--------|------|-------------|
| raw_text | str | Original listing text |
| link | str | Listing URL |
| page_found | int | Page number where found |
| scrape_timestamp | datetime | When scraped |
| price | float | Monthly rent in EUR |
| size | int | Apartment size in m² |
| rooms | int | Number of rooms |
| district | int | Vienna postal code (1010-1230) |
| has_balkon | int | Has balcony (0/1) |
| has_terrasse | int | Has terrace (0/1) |
| is_neubau | int | New building (0/1) |
| is_furnished | int | Furnished (0/1) |

### Cleaned Data (vienna_rent_clean.csv)

Additional derived columns:
- `price_per_m2`: Price per square meter (EUR/m²)
- `has_outdoor`: Combined outdoor space indicator
- `floor`: Floor level (0 = ground floor)
- `is_temporary`: Temporary lease flag

## Key Insights

Based on current dataset (300 listings across 23 districts):

**Price Drivers:**
- Outdoor space: +18.9% premium on price per m²
- Furnished apartments: +46.2% premium on total rent
- Neubau properties: -13.1% (location-dependent)

**Market Overview:**
- Average rent: €22.56/m²
- Most expensive district: 1010 (Innere Stadt) - €32.26/m²
- Cheapest districts: 1100, 1210, 1220 - €18-20/m²
- Most common: 2-room apartments (43% of listings)

**Feature Coverage:**
- 69% of listings include outdoor space
- 15.3% are new buildings (Neubau)
- 3% are furnished
- 0.7% are temporary leases

## Technical Details

### Scraping Strategy

- **Target:** willhaben.at rental listings for Vienna
- **Method:** Selenium WebDriver with Chrome
- **Anti-detection:** Randomized delays, human-like scrolling, realistic user agent
- **Performance:** ~6.6 seconds per page
- **Resilience:** Retry logic, checkpoint saves, graceful error handling

### Feature Extraction

Uses regex patterns optimized for German/Austrian real estate terminology:
- Rooms: `(\d+)[-\s]*(?:Zimmer|Zi\b)`
- District: `(1\d{3})` (postal codes 1000-1999)
- Size: `(\d+)\s*m²`
- Price: `€\s*([\d.,]+)` with German number format conversion

### Map Generation

- **Base data:** Official Open Government Data Vienna (ogdwien:BEZIRKSGRENZEOGD)
- **Library:** Folium with plugins (Fullscreen, MiniMap, MeasureControl)
- **Color scheme:** Red-Yellow-Green reversed (red = expensive, green = cheap)
- **Bins:** Custom price ranges [10, 15, 18, 21, 25, 30, 40] EUR/m²

## Dependencies

Core libraries:
- `selenium`: Web scraping automation
- `pandas`: Data manipulation and analysis
- `folium`: Interactive map generation
- `requests`: HTTP requests for map data

Full list in `requirements.txt`

## Future Enhancements

Potential improvements:
- Historical trend tracking (price changes over time)
- Machine learning price prediction model
- Email alerts for new listings matching criteria
- Comparison with other Austrian cities
- Integration with public transport data (commute times)

## License

This project is for educational and personal use only. Respect willhaben.at's terms of service and robots.txt when scraping.

## Author

Created as a data analysis portfolio project.

Last updated: January 2026
