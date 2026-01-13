import subprocess
import sys
import os
from datetime import datetime

PIPELINE = [
    ("1. Scraping", "scripts/scraper.py"),
    ("2. Cleaning", "scripts/cleaner.py"),
    ("3. Tracking", "scripts/tracker.py"),
    ("4. Mapping", "scripts/mapper.py"),
    ("5. Training", "scripts/train_model.py")
]

def run_step(name, script_path):
    print(f"\n{'-'*60}")
    print(f"STARTING: {name}")
    print(f"{'-'*60}")
    
    python_exe = sys.executable
    
    if not os.path.exists(script_path):
        print(f"ERROR: Script not found at {script_path}")
        # We don't exit for mapping/training as they are optional
        return

    result = subprocess.run([python_exe, script_path], capture_output=False)
    
    if result.returncode != 0:
        print(f"\nERROR in {name}. Pipeline stopped.")
        sys.exit(1)
    else:
        print(f"\nSUCCESS: {name} completed.")

def main():
    start_time = datetime.now()
    print(f"Vienna Rent Pipeline started at {start_time.strftime('%H:%M:%S')}")
    
    if not os.path.exists("data"):
        os.makedirs("data", exist_ok=True)

    for name, script in PIPELINE:
        run_step(name, script)

    duration = datetime.now() - start_time
    print(f"\n{'='*60}")
    print(f"PIPELINE FINISHED in {duration.total_seconds():.1f} seconds")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()