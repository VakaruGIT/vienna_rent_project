import pandas as pd
import random

# Simulate tomorrow's scrape
df = pd.read_csv('data/vienna_rent.csv')

# 1. Remove 10% (rented out)
remove_count = int(len(df) * 0.10)
removed_indices = random.sample(range(len(df)), remove_count)
df_tomorrow = df.drop(removed_indices).copy()

# 2. Change 5% prices
price_change_count = int(len(df_tomorrow) * 0.05)
change_indices = random.sample(range(len(df_tomorrow)), price_change_count)

for idx in change_indices:
    loc = df_tomorrow.index[idx]
    original_price = df_tomorrow.loc[loc, 'price']
    if pd.notna(original_price):
        if random.random() < 0.7:
            change = random.uniform(-0.15, -0.05)
        else:
            change = random.uniform(0.03, 0.10)
        df_tomorrow.loc[loc, 'price'] = original_price * (1 + change)

# 3. Add new listings
new_listings = df.sample(n=15).copy()
new_listings['link'] = new_listings['link'] + '_NEW' + str(random.randint(1000, 9999))
df_tomorrow = pd.concat([df_tomorrow, new_listings], ignore_index=True)

# Save
df_tomorrow.to_csv('data/vienna_rent.csv', index=False)

print(f'Simulated tomorrow: {len(df_tomorrow)} listings')
print(f'  Removed: {remove_count}')
print(f'  Price changes: {price_change_count}')
print(f'  New: {len(new_listings)}')
