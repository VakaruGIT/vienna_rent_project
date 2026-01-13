"""
DEEP SCRAPER - Clicks into detail pages for complete data extraction

This is 10x slower but extracts 5x more valuable features:
- GPS coordinates (for distance calculations)
- Transportation data (U-Bahn, S-Bahn nearby)
- Building features (elevator, parking, year built)
- Financial details (deposit, Betriebskosten)
- Exact availability date
- Number of photos (quality indicator)

Use this when:
1. You need training data for advanced ML models
2. Building a commercial product
3. Want to add geospatial features (distance to transport)

Run time: ~5 seconds per listing (300 listings = 25 minutes)
"""

import time
import pandas as pd
import os
import re
import random
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- CONFIGURATION ---
BASE_URL = "https://www.willhaben.at/iad/immobilien/mietwohnungen/wien"
PAGES_TO_SCRAPE = 3  # Start small with deep scraping
HEADLESS = True
DETAIL_PAGE_SCRAPING = True  # Set to False for fast list-only scraping
MAX_DETAILS_PER_PAGE = 10  # Limit detail pages per listing page (to control time)
# ---------------------

script_dir = os.path.dirname(os.path.abspath(__file__))
output_path = os.path.join(script_dir, "..", "data", "vienna_rent_detailed.csv")

def extract_detail_page_data(driver, url):
    """
    Extract ALL available data from a listing detail page
    This is where the gold is hidden!
    """
    try:
        driver.get(url)
        time.sleep(random.uniform(1.0, 2.0))  # Realistic human delay
        
        data = {'detail_scraped': True}
        
        # Wait for page load
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except:
            return {'detail_scraped': False, 'error': 'page_load_timeout'}
        
        page_text = driver.page_source.lower()
        
        # === LOCATION DATA ===
        # Try to find coordinates (often in meta tags or scripts)
        coord_match = re.search(r'latitude["\s:]+(\d+\.\d+)', page_text)
        if coord_match:
            data['latitude'] = float(coord_match.group(1))
        
        coord_match = re.search(r'longitude["\s:]+(\d+\.\d+)', page_text)
        if coord_match:
            data['longitude'] = float(coord_match.group(1))
        
        # Street address (often partially shown)
        address_match = re.search(r'(\d{4}\s+wien[,\s]+[^<]+)', page_text, re.IGNORECASE)
        if address_match:
            data['address'] = address_match.group(1).strip()
        
        # === BUILDING FEATURES ===
        data['has_elevator'] = 1 if 'aufzug' in page_text or 'lift' in page_text else 0
        data['has_parking'] = 1 if any(word in page_text for word in ['parkplatz', 'garage', 'stellplatz']) else 0
        data['has_garden'] = 1 if 'garten' in page_text else 0
        data['has_basement'] = 1 if 'keller' in page_text else 0
        data['pets_allowed'] = 1 if 'haustiere' in page_text and 'erlaubt' in page_text else 0
        
        # Year built
        year_match = re.search(r'baujahr[:\s]+(\d{4})', page_text)
        if year_match:
            data['year_built'] = int(year_match.group(1))
        
        # Floor (more precise extraction from detail page)
        floor_match = re.search(r'(\d+)[.\s]*(?:stock|etage|obergeschoss)', page_text)
        if floor_match:
            data['floor'] = int(floor_match.group(1))
        elif 'erdgeschoss' in page_text or 'eg ' in page_text:
            data['floor'] = 0
        
        # === FINANCIAL DETAILS ===
        # Deposit
        deposit_match = re.search(r'kaution[:\s]*€?\s*([\d.,]+)', page_text)
        if deposit_match:
            raw = deposit_match.group(1).replace('.', '').replace(',', '.')
            try:
                data['deposit'] = float(raw)
            except:
                pass
        
        # Betriebskosten (operating costs)
        betrieb_match = re.search(r'betriebskosten[:\s]*€?\s*([\d.,]+)', page_text)
        if betrieb_match:
            raw = betrieb_match.group(1).replace('.', '').replace(',', '.')
            try:
                data['betriebskosten'] = float(raw)
            except:
                pass
        
        # Heating costs
        heating_match = re.search(r'heizkosten[:\s]*€?\s*([\d.,]+)', page_text)
        if heating_match:
            raw = heating_match.group(1).replace('.', '').replace(',', '.')
            try:
                data['heating_costs'] = float(raw)
            except:
                pass
        
        # === TIMING ===
        # Availability date
        date_match = re.search(r'verfügbar ab[:\s]*(\d{1,2})[.\s]*(\d{1,2})[.\s]*(\d{4})', page_text)
        if date_match:
            data['available_date'] = f"{date_match.group(3)}-{date_match.group(2)}-{date_match.group(1)}"
        elif 'sofort' in page_text or 'ab sofort' in page_text:
            data['available_date'] = 'immediate'
        
        # === QUALITY INDICATORS ===
        # Count number of images (more photos = serious listing)
        images = driver.find_elements(By.CSS_SELECTOR, "img[src*='willhaben'], img[data-src*='willhaben']")
        data['photo_count'] = len(images)
        
        # Description length (longer = more detailed)
        description_elem = driver.find_elements(By.CSS_SELECTOR, "[class*='description'], [class*='text']")
        desc_text = " ".join([elem.text for elem in description_elem])
        data['description_length'] = len(desc_text)
        
        # === TRANSPORTATION (Pattern recognition in text) ===
        # U-Bahn mentions
        ubahn_mentions = re.findall(r'u[1-6]\b', page_text)
        if ubahn_mentions:
            data['ubahn_lines'] = ','.join(set(ubahn_mentions))
            data['ubahn_count'] = len(set(ubahn_mentions))
        else:
            data['ubahn_count'] = 0
        
        # General public transport mention
        data['public_transport_mentioned'] = 1 if any(word in page_text for word in 
            ['u-bahn', 's-bahn', 'straßenbahn', 'öffi', 'verkehrsanbindung']) else 0
        
        # Distance mentions (e.g., "5 min zur U-Bahn")
        distance_match = re.search(r'(\d+)\s*(?:min|minuten).*?(?:u-bahn|s-bahn|station)', page_text)
        if distance_match:
            data['transit_walk_min'] = int(distance_match.group(1))
        
        # === ENERGY RATING ===
        # Austrian HWB scale (kWh/m²/year)
        energy_match = re.search(r'hwb[:\s]*([\d.,]+)', page_text)
        if energy_match:
            raw = energy_match.group(1).replace(',', '.')
            try:
                data['energy_rating_hwb'] = float(raw)
            except:
                pass
        
        # Energy class (A++ to G)
        energy_class_match = re.search(r'energieeffizienzklasse[:\s]*([a-g][+]*)', page_text)
        if energy_class_match:
            data['energy_class'] = energy_class_match.group(1).upper()
        
        return data
        
    except Exception as e:
        return {'detail_scraped': False, 'error': str(e)}

def scrape_with_details(driver, wait, page_number):
    """Scrape list page + detail pages"""
    
    if page_number == 1:
        current_url = BASE_URL
    else:
        current_url = f"{BASE_URL}?page={page_number}"
    
    print(f"\n--- Page {page_number} ---")
    driver.get(current_url)
    
    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/d/']")))
    except:
        print("  Page load timeout")
        return []
    
    # Handle cookies
    if page_number == 1:
        try:
            WebDriverWait(driver, 2).until(
                EC.element_to_be_clickable((By.ID, "didomi-notice-agree-button"))
            ).click()
        except:
            pass
    
    # Get listing links
    ads = driver.find_elements(By.CSS_SELECTOR, "a[href*='/d/']")
    links = []
    for ad in ads[:MAX_DETAILS_PER_PAGE]:  # Limit to prevent extremely long runs
        link = ad.get_attribute("href")
        if link and '/d/' in link:
            links.append(link)
    
    links = list(set(links))  # Remove duplicates
    print(f"Found {len(links)} unique listings, will scrape details for {min(len(links), MAX_DETAILS_PER_PAGE)}")
    
    all_data = []
    
    for idx, link in enumerate(links[:MAX_DETAILS_PER_PAGE], 1):
        print(f"  [{idx}/{min(len(links), MAX_DETAILS_PER_PAGE)}] Scraping detail page...")
        
        # Get detailed data
        detail_data = extract_detail_page_data(driver, link)
        
        # Add metadata
        listing = {
            'link': link,
            'page_found': page_number,
            'scrape_timestamp': datetime.now().isoformat(),
            **detail_data
        }
        
        all_data.append(listing)
        
        # Random delay between detail pages (anti-detection)
        if idx < len(links):
            time.sleep(random.uniform(2.0, 4.0))
    
    return all_data

# === MAIN EXECUTION ===
print("="*60)
print("VIENNA RENT DEEP SCRAPER")
print("="*60)
print(f"Target: {PAGES_TO_SCRAPE} pages")
print(f"Detail scraping: {'ENABLED' if DETAIL_PAGE_SCRAPING else 'DISABLED'}")
print(f"Max details per page: {MAX_DETAILS_PER_PAGE}")
print(f"Est. time: {PAGES_TO_SCRAPE * MAX_DETAILS_PER_PAGE * 3 / 60:.1f} minutes")
print("="*60)

options = Options()
options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
options.add_argument("--disable-blink-features=AutomationControlled")

if HEADLESS:
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")

try:
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 10)
    
    all_data = []
    start_time = time.time()
    
    for page_num in range(1, PAGES_TO_SCRAPE + 1):
        page_data = scrape_with_details(driver, wait, page_num)
        all_data.extend(page_data)
        
        # Delay between pages
        if page_num < PAGES_TO_SCRAPE:
            time.sleep(random.uniform(3.0, 5.0))
    
    elapsed = time.time() - start_time
    
    # Save results
    if all_data:
        df = pd.DataFrame(all_data)
        df.to_csv(output_path, index=False)
        
        print("\n" + "="*60)
        print("SCRAPING COMPLETE")
        print("="*60)
        print(f"\nTotal listings scraped: {len(df)}")
        print(f"Time elapsed: {elapsed:.1f}s ({elapsed/60:.1f} minutes)")
        print(f"Avg time per listing: {elapsed/len(df):.1f}s")
        print(f"\nColumns extracted: {len(df.columns)}")
        print(f"File: {output_path}")
        
        # Show data quality metrics
        print("\n--- Data Quality ---")
        quality_cols = ['latitude', 'has_elevator', 'deposit', 'ubahn_count', 'photo_count']
        for col in quality_cols:
            if col in df.columns:
                coverage = df[col].notna().sum() / len(df) * 100
                print(f"{col:20s}: {coverage:.1f}% coverage")
    
except KeyboardInterrupt:
    print("\nScraping interrupted")
except Exception as e:
    print(f"\nError: {e}")
finally:
    driver.quit()
