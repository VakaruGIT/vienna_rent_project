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
PAGES_TO_SCRAPE = 10  # Increased from 3 to get more data
HEADLESS = True  # Run without browser window (faster)
CHECKPOINT_EVERY = 3  # Save progress every N pages
# ---------------------

script_dir = os.path.dirname(os.path.abspath(__file__))
output_path = os.path.join(script_dir, "..", "data", "vienna_rent.csv")
checkpoint_path = os.path.join(script_dir, "..", "data", "scrape_checkpoint.csv")

def load_existing_links():
    """Load already scraped links to avoid duplicates"""
    existing = set()
    if os.path.exists(output_path):
        try:
            df = pd.read_csv(output_path)
            if 'link' in df.columns:
                existing = set(df['link'].dropna())
                print(f"Loaded {len(existing)} existing listings")
        except:
            pass
    return existing

def extract_structured_data(text):
    """Extract structured fields during scraping for better data quality"""
    data = {}
    
    # Price
    match = re.search(r'€\s*([\d.,]+)', text)
    if match:
        raw = match.group(1).replace('.', '').replace(',', '.')
        try:
            data['price'] = float(raw)
        except:
            data['price'] = None
    else:
        data['price'] = None
    
    # Size
    match = re.search(r'(\d+)\s*m²', text)
    data['size'] = int(match.group(1)) if match else None
    
    # Rooms
    match = re.search(r'(\d+)[-\s]*(?:Zimmer|Zi\b)', text, re.IGNORECASE)
    data['rooms'] = int(match.group(1)) if match else None
    
    # District
    match = re.search(r'(1\d{3})', text)
    data['district'] = int(match.group(1)) if match else None
    
    # Features (binary flags)
    text_lower = text.lower()
    data['has_balkon'] = 1 if 'balkon' in text_lower else 0
    data['has_terrasse'] = 1 if 'terrasse' in text_lower else 0
    data['is_neubau'] = 1 if 'neubau' in text_lower else 0
    data['is_furnished'] = 1 if 'möbliert' in text_lower else 0
    
    return data

def turbo_scroll(driver):
    """Optimized scroll with random delays for anti-detection"""
    print("  >> Turbo Scroll activated...")
    last_height = driver.execute_script("return document.body.scrollHeight")
    
    while True:
        # Random scroll size for more human-like behavior
        scroll_amount = random.randint(1000, 1400)
        driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
        
        # Random delay (anti-detection)
        time.sleep(random.uniform(0.3, 0.6))
        
        new_height = driver.execute_script("return document.body.scrollHeight")
        current_pos = driver.execute_script("return window.pageYOffset + window.innerHeight")
        
        if current_pos >= new_height:
            break
        
        if new_height == last_height:
            driver.execute_script("window.scrollBy(0, 500);")
            time.sleep(0.4)
            if driver.execute_script("return document.body.scrollHeight") == last_height:
                break
        
        last_height = new_height

def save_checkpoint(data, page_num):
    """Save progress to recover from crashes"""
    df = pd.DataFrame(data)
    df.to_csv(checkpoint_path, index=False)
    print(f"  [Checkpoint saved at page {page_num}]")

def scrape_page(driver, wait, page_number, existing_links):
    """Scrape a single page with error handling"""
    if page_number == 1:
        current_url = BASE_URL
    else:
        current_url = f"{BASE_URL}?page={page_number}"
    
    print(f"\n--- Page {page_number} ---")
    
    # Retry logic for page load
    max_retries = 3
    for attempt in range(max_retries):
        try:
            driver.get(current_url)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/d/']")))
            break
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"  Retry {attempt + 1}/{max_retries}...")
                time.sleep(2)
            else:
                print(f"  Failed to load page {page_number}")
                return []
    
    # Handle Cookies (First page only)
    if page_number == 1:
        try:
            WebDriverWait(driver, 2).until(
                EC.element_to_be_clickable((By.ID, "didomi-notice-agree-button"))
            ).click()
            print("  Cookies accepted")
        except:
            pass
    
    # Scroll to load all listings
    turbo_scroll(driver)
    
    # Scrape listings
    ads = driver.find_elements(By.CSS_SELECTOR, "a[href*='/d/']")
    
    page_data = []
    new_count = 0
    duplicate_count = 0
    
    for ad_link in ads:
        try:
            link = ad_link.get_attribute("href")
            
            # Skip duplicates
            if link in existing_links:
                duplicate_count += 1
                continue
            
            txt = ad_link.text
            if "€" in txt:
                # Extract structured data immediately
                structured = extract_structured_data(txt)
                
                listing = {
                    "raw_text": txt.replace("\n", " | "),
                    "link": link,
                    "page_found": page_number,
                    "scrape_timestamp": datetime.now().isoformat(),
                    **structured  # Unpack structured fields
                }
                
                page_data.append(listing)
                existing_links.add(link)
                new_count += 1
        except Exception as e:
            continue
    
    print(f"-> New: {new_count} | Duplicates: {duplicate_count} | Total on page: {len(ads)}")
    return page_data

# 1. SETUP
options = Options()
options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--no-sandbox")

if HEADLESS:
    options.add_argument("--headless=new")  # New headless mode
    options.add_argument("--window-size=1920,1080")
    print("Running in HEADLESS mode (faster)")
else:
    print("Running with visible browser")

# Load existing data
existing_links = load_existing_links()

print(f"\nStarting Vienna Rent Scraper v2.0")
print(f"Target: {PAGES_TO_SCRAPE} pages")
print("="*60)

try:
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 10)
    
    all_ads_data = []
    start_time = time.time()
    
    # 2. THE LOOP
    for page_number in range(1, PAGES_TO_SCRAPE + 1):
        page_data = scrape_page(driver, wait, page_number, existing_links)
        all_ads_data.extend(page_data)
        
        # Checkpoint save
        if page_number % CHECKPOINT_EVERY == 0 and all_ads_data:
            save_checkpoint(all_ads_data, page_number)
        
        # Anti-detection: random delay between pages
        if page_number < PAGES_TO_SCRAPE:
            delay = random.uniform(1.5, 3.0)
            time.sleep(delay)
    
    elapsed = time.time() - start_time
    
    # 3. SAVE FINAL RESULTS
    if all_ads_data:
        # Combine with existing data if any
        if os.path.exists(output_path):
            try:
                existing_df = pd.read_csv(output_path)
                new_df = pd.DataFrame(all_ads_data)
                combined_df = pd.concat([existing_df, new_df], ignore_index=True)
                # Remove duplicates based on link
                combined_df = combined_df.drop_duplicates(subset=['link'], keep='last')
                combined_df.to_csv(output_path, index=False)
                print(f"\n✅ MERGED with existing data")
                print(f"   New listings: {len(new_df)}")
                print(f"   Total in database: {len(combined_df)}")
            except:
                # If merge fails, just save new data
                df = pd.DataFrame(all_ads_data)
                df.to_csv(output_path, index=False)
                print(f"\n✅ SAVED new data: {len(df)} listings")
        else:
            df = pd.DataFrame(all_ads_data)
            df.to_csv(output_path, index=False)
            print(f"\n✅ SAVED: {len(df)} listings")
        
        print(f"   File: {output_path}")
        print(f"   Time elapsed: {elapsed:.1f}s ({elapsed/PAGES_TO_SCRAPE:.1f}s per page)")
        
        # Clean up checkpoint
        if os.path.exists(checkpoint_path):
            os.remove(checkpoint_path)
    else:
        print("\n⚠️  No new data scraped")
    
except KeyboardInterrupt:
    print("\n\n⚠️  Scraping interrupted by user")
    if all_ads_data:
        print("Saving partial results...")
        df = pd.DataFrame(all_ads_data)
        df.to_csv(checkpoint_path, index=False)
        print(f"Partial data saved to checkpoint: {len(df)} listings")
except Exception as e:
    print(f"\n❌ Error: {e}")
    if all_ads_data:
        df = pd.DataFrame(all_ads_data)
        df.to_csv(checkpoint_path, index=False)
        print(f"Partial data saved: {len(df)} listings")
finally:
    driver.quit()
    print("\nBrowser closed")
