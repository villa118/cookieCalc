import pandas as pd
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt

def cost_per_unit_calc(cost, units):
    return cost/units

# Calculate all the per unit costs
egg_cost = cost_per_unit_calc(22.24,90)
butter_cost = cost_per_unit_calc(12.18,16)
flour_cost = cost_per_unit_calc(6,5)
sugar_cost = cost_per_unit_calc(4.5,4)
vanilla_cost = cost_per_unit_calc(13,11)
baking_powder_cost = cost_per_unit_calc(2.79,8)
powder_sugar_cost = cost_per_unit_calc(2.6,2)


# Create the dataframe
ingredient_data = [
    {'name': 'egg', 'unit_cost': egg_cost, 'quantity_used': 4},
    {'name': 'butter', 'unit_cost': butter_cost, 'quantity_used': 8},
    {'name': 'flour', 'unit_cost': flour_cost, 'quantity_used': 3},
    {'name': 'sugar', 'unit_cost': sugar_cost, 'quantity_used': 1.763698},
    {'name': 'vanilla', 'unit_cost': vanilla_cost, 'quantity_used': 2},
    {'name': 'powdered_sugar', 'unit_cost': powder_sugar_cost , 'quantity_used': 4},
]

df = pd.DataFrame(ingredient_data)
df['total_cost'] = df['unit_cost'] * df['quantity_used']

# Calculate calues
cookie_yield = 50
cookie_price = 0.5
revenue = cookie_price * cookie_yield
total_cost = df['total_cost'].sum()
profit = revenue - total_cost
profit_per_cookie = profit / cookie_yield

# Display information
print(df)
print(f"\nTotal cost: ${total_cost:.2f}")
print(f"Revenue: ${revenue:.2f}")
print(f"Profit: ${profit:.2f}")
print(f"Profit per cookie: ${profit_per_cookie:.2f}")

# Create chart data
labels = ['Total Cost', 'Total Revenue', 'Profit']
values = [total_cost, revenue, profit]

# Plot
plt.figure(figsize=(8, 5))
plt.bar(labels, values)
plt.title("Profit vs Cost for Cookie Batch")
plt.ylabel("USD ($)")
plt.grid(axis='y', linestyle='--', alpha=0.5)

# Annotate bars
for i, v in enumerate(values):
    plt.text(i, v + 0.5, f"${v:.2f}", ha='center')

plt.tight_layout()
plt.show()