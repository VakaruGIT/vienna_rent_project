import time
import pandas as pd
import os
import random
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- CONFIGURATION ---
BASE_URL = "https://www.willhaben.at/iad/immobilien/mietwohnungen/wien"
PAGES_TO_SCRAPE = 10 
HEADLESS = True 
CHECKPOINT_EVERY = 3
# ---------------------

script_dir = os.path.dirname(os.path.abspath(__file__))
output_path = os.path.join(script_dir, "..", "data", "vienna_rent_raw.csv")
checkpoint_path = os.path.join(script_dir, "..", "data", "scrape_checkpoint.csv")

def turbo_scroll(driver):
    """Optimized scroll with random delays for anti-detection"""
    print("  >> Turbo Scroll activated...")
    last_height = driver.execute_script("return document.body.scrollHeight")
    
    while True:
        scroll_amount = random.randint(1000, 1400)
        driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
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
    df = pd.DataFrame(data)
    df.to_csv(checkpoint_path, index=False)
    print(f"  [Checkpoint saved at page {page_num}]")

def scrape_page(driver, wait, page_number):
    if page_number == 1:
        current_url = BASE_URL
    else:
        current_url = f"{BASE_URL}?page={page_number}"
    
    print(f"\n--- Page {page_number} ---")
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            driver.get(current_url)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/d/']")))
            break
        except Exception:
            if attempt < max_retries - 1:
                print(f"  Retry {attempt + 1}/{max_retries}...")
                time.sleep(2)
            else:
                print(f"  Failed to load page {page_number}")
                return []
    
    if page_number == 1:
        try:
            WebDriverWait(driver, 2).until(
                EC.element_to_be_clickable((By.ID, "didomi-notice-agree-button"))
            ).click()
            print("  Cookies accepted")
        except:
            pass
    
    turbo_scroll(driver)
    
    ads = driver.find_elements(By.CSS_SELECTOR, "a[href*='/d/']")
    
    page_data = []
    seen_links_on_page = set()
    
    for ad_link in ads:
        try:
            link = ad_link.get_attribute("href")
            
            if link in seen_links_on_page:
                continue
            
            txt = ad_link.text
            if "€" in txt:
                listing = {
                    "raw_text": txt.replace("\n", " | "),
                    "link": link,
                    "page_found": page_number,
                    "scrape_timestamp": datetime.now().isoformat()
                }
                
                page_data.append(listing)
                seen_links_on_page.add(link)
        except Exception:
            continue
    
    print(f"-> Collected: {len(page_data)} listings")
    return page_data

# --- MAIN EXECUTION ---
options = Options()
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--no-sandbox")

if HEADLESS:
    options.add_argument("--headless=new")
    print("Running in HEADLESS mode")
else:
    print("Running with visible browser")

print(f"\nStarting Vienna Rent Scraper")
print(f"Target: {PAGES_TO_SCRAPE} pages")
print("-" * 60)

try:
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 10)
    
    all_ads_data = []
    start_time = time.time()
    
    for page_number in range(1, PAGES_TO_SCRAPE + 1):
        page_data = scrape_page(driver, wait, page_number)
        all_ads_data.extend(page_data)
        
        if page_number % CHECKPOINT_EVERY == 0 and all_ads_data:
            save_checkpoint(all_ads_data, page_number)
        
        if page_number < PAGES_TO_SCRAPE:
            delay = random.uniform(1.5, 3.0)
            time.sleep(delay)
    
    elapsed = time.time() - start_time
    
    if all_ads_data:
        df = pd.DataFrame(all_ads_data)
        df.to_csv(output_path, index=False)
        print(f"\nSUCCESS: Snapshot saved to {output_path}")
        print(f"Total listings: {len(df)}")
        print(f"Time elapsed: {elapsed:.1f}s")
        
        if os.path.exists(checkpoint_path):
            os.remove(checkpoint_path)
    else:
        print("\nWARNING: No data scraped")
    
except Exception as e:
    print(f"\nERROR: {e}")
    if all_ads_data:
        df = pd.DataFrame(all_ads_data)
        df.to_csv(checkpoint_path, index=False)
        print(f"Partial data saved to checkpoint")
finally:
    driver.quit()
    print("\nBrowser closed")