import time
import pandas as pd
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

# --- CONFIGURATION ---
BASE_URL = "https://www.willhaben.at/iad/immobilien/mietwohnungen/wien"
PAGES_TO_SCRAPE = 3  # Start with 3 pages to test
# ---------------------

def smart_scroll(driver):
    print("  Beginning smart scroll...")
    
    # Safety Brake: Don't scroll more than 30 times (Willhaben pages aren't that long)
    max_scrolls = 30 
    
    last_height = driver.execute_script("return document.body.scrollHeight")
    
    for i in range(max_scrolls):
        # Scroll down by 1000 pixels
        driver.execute_script("window.scrollBy(0, 1000);")
        
        # Wait for "Lazy Load" images to appear
        time.sleep(1.5)
        
        # Calculate new height
        new_height = driver.execute_script("return document.body.scrollHeight")
        
        # Check if we are near the bottom
        # (window.scrollY + window.height) == total_height
        current_pos = driver.execute_script("return window.pageYOffset + window.innerHeight")
        
        # If we are within 200 pixels of the bottom, STOP.
        if current_pos >= (new_height - 200):
            print("  Reached bottom (Position Check).")
            break
            
        # OR: If the page height didn't change after we scrolled, we are stuck or done.
        if new_height == last_height:
            print("  Height didn't change. We are likely at the bottom.")
            break
            
        last_height = new_height

# 1. SETUP
options = Options()
# Using a standard User Agent
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
options.add_argument("--disable-blink-features=AutomationControlled")

print("Starting Auto-Scroll Robot...")
driver = webdriver.Chrome(options=options)

all_ads_data = []

# 2. THE LOOP
for page_number in range(1, PAGES_TO_SCRAPE + 1):
    
    if page_number == 1:
        current_url = BASE_URL
    else:
        current_url = f"{BASE_URL}?page={page_number}"
    
    print(f"--- Loading Page {page_number} ---")
    driver.get(current_url)
    time.sleep(3) # Initial load

    # Handle Cookies (First page only)
    if page_number == 1:
        try:
            driver.find_element(By.ID, "didomi-notice-agree-button").click()
            time.sleep(1)
        except:
            pass
            
    # --- THE MAGIC FIX: SCROLL BEFORE SCRAPING ---
    smart_scroll(driver)
    
    # 3. NOW SCRAPE (Everything should be loaded)
    print("  Scanning all loaded links...")
    ads = driver.find_elements(By.CSS_SELECTOR, "a[href*='/d/']")
    
    page_count = 0
    for ad_link in ads:
        try:
            text_content = ad_link.text
            url_link = ad_link.get_attribute("href")
            
            # Filter valid ads
            if "€" in text_content or "m²" in text_content:
                clean_text = text_content.replace("\n", " | ")
                
                entry = {
                    "raw_text": clean_text,
                    "link": url_link,
                    "page_found": page_number
                }
                all_ads_data.append(entry)
                page_count += 1
        except:
            continue
            
    print(f"-> Collected {page_count} ads from Page {page_number}")

# 4. SAVE
print(f"Total Ads Collected: {len(all_ads_data)}")
if len(all_ads_data) > 0:
    df = pd.DataFrame(all_ads_data)
    df.to_csv("vienna_rent_full_scroll.csv", index=False)
    print("Success! Open 'vienna_rent_full_scroll.csv'")
else:
    print("Something went wrong. Still 0.")

driver.quit()