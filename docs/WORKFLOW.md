# Daily Workflow - Quick Reference

## 📅 Every Morning (5 minutes)

Run these three commands in sequence:

```bash
# 1. Scrape today's listings
python scripts/scraper.py

# 2. Process the raw data
python scripts/cleaner.py

# 3. Add to historical database
python scripts/tracker.py
```

## 📊 Analysis (Whenever Needed)

```bash
# Generate interactive map
python scripts/mapper.py

# Train ML model
python scripts/train_model.py
```

---

## File Structure (Simplified)

```
data/
├── vienna_rent_raw.csv          # Today's scrape (overwritten daily)
├── vienna_rent_clean.csv        # Latest processed data
├── vienna_rent_history.csv      # Historical database (NEVER DELETE!)
└── vienna_rent_map.html         # Interactive visualization
```

**Key Principle:** 
- `raw.csv` = Temporary (overwritten daily)
- `clean.csv` = Latest snapshot (overwritten daily)
- `history.csv` = Permanent (append-only, grows over time)

---

## Why This Workflow Works

### Week 1-2: Foundation
- Build baseline dataset (300+ listings/day × 14 days = 4,200 records)
- Establish district price averages
- Identify initial trends

### Week 3-4: Insights Emerge
- Track which listings rent fast vs slow
- Detect price changes (landlords adjusting rates)
- Identify hot markets (high turnover districts)

### Month 2+: Competitive Advantage
- ML model accuracy improves (R² 0.31 → 0.75+)
- Seasonal patterns become visible
- Predict "best time to rent" by district
- Calculate typical "days on market"

---

## Automation Ideas

### Option 1: Manual (Simple)
Add this to your morning routine (5 min):
1. Open terminal
2. Run the 3 commands
3. Check output for errors

### Option 2: Cron Job (macOS/Linux)
```bash
# Edit crontab
crontab -e

# Add this line (runs daily at 8am)
0 8 * * * cd /Users/andei/Desktop/Personal/vienna_rent_project && source .venv/bin/activate && python scripts/scraper.py && python scripts/cleaner.py && python scripts/tracker.py
```

### Option 3: GitHub Actions (Advanced)
- Runs automatically in the cloud
- No need to keep computer on
- Requires repository setup + ChromeDriver config
- See README for future implementation

---

## Troubleshooting

**Error: "vienna_rent_raw.csv not found"**
- Run `scraper.py` first

**Error: "vienna_rent_clean.csv not found"**
- Run `cleaner.py` before `tracker.py`

**Error: ChromeDriver version mismatch**
```bash
# Check Chrome version
google-chrome --version

# Download matching ChromeDriver from:
# https://chromedriver.chromium.org/downloads
```

**Slow scraping (>10s per page)**
- Check internet connection
- Reduce `PAGES_TO_SCRAPE` in scraper.py
- Consider running during off-peak hours

---

## Quick Stats

After 30 days of daily scraping, you'll have:
- ~9,000 historical records
- ~500 unique listings tracked
- Price trends across 23 districts
- ML model R² of 0.70-0.85
- Data valuable to real estate agents (€200/month consulting potential)

---

**Last Updated:** January 13, 2026
