import pickle

# Load the model
with open('data/rent_price_model.pkl', 'rb') as f:
    model = pickle.load(f)

print('='*60)
print('RENT PRICE CALCULATOR - TEST')
print('='*60)

# Test Case 1: Typical 2-room in District 1050 with balcony
print('\nTest 1: 50m², 2 rooms, District 1050, with balcony')
pred1 = model.predict([[50, 2, 1050, 1, 0, 0]])
print(f'   Predicted rent: €{pred1[0]:.0f}/month')
print(f'   Price per m²: €{pred1[0]/50:.2f}')

# Test Case 2: Luxury 3-room in District 1010 (city center)
print('\nTest 2: 80m², 3 rooms, District 1010, no balcony')
pred2 = model.predict([[80, 3, 1010, 0, 0, 0]])
print(f'   Predicted rent: €{pred2[0]:.0f}/month')
print(f'   Price per m²: €{pred2[0]/80:.2f}')

# Test Case 3: New building in outer district
print('\nTest 3: 60m², 2 rooms, District 1220, Neubau with terrace')
pred3 = model.predict([[60, 2, 1220, 1, 1, 0]])
print(f'   Predicted rent: €{pred3[0]:.0f}/month')
print(f'   Price per m²: €{pred3[0]/60:.2f}')

# Test Case 4: Furnished studio
print('\nTest 4: 35m², 1 room, District 1060, furnished')
pred4 = model.predict([[35, 1, 1060, 0, 0, 1]])
print(f'   Predicted rent: €{pred4[0]:.0f}/month')
print(f'   Price per m²: €{pred4[0]/35:.2f}')

print('\n' + '='*60)
