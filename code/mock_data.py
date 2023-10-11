import json
import random

# Setting the seed for repeatability
random.seed(42)

def get_json_from_csv(csv_file):
    # Read the csv file and convert it to a list of dictionaries
    with open(csv_file, 'r') as f:
        csv_data = f.read().splitlines()

    # The first line of the csv file contains the column names
    column_names = csv_data[0].split(',')
    data = []
    for entry in csv_data[1:]:
        entry_values = entry.split(',')
        entry_dict = dict(zip(column_names, entry_values))
        data.append(entry_dict)

    # Return the sorted names as a list
    return data


def relay_ordering(data):
    # Sort the data based on walking speed, then gender (with females first in case of ties)
    sorted_data = sorted(data, key=lambda x: (x['WalkingSpeed'], 0 if x['Gender'] == 'Female' else 1))

    # Return the sorted names as a list
    return [entry['Name'] for entry in sorted_data]


# Test the function
data = get_json_from_csv("../data/mock_data.csv")
print(f"Original data: {relay_ordering(data)}")
print(data)

# Extract 4 random subsets of the list of people
subset_size = len(data) // 2  # Let's say we want half of the data, but you can change this number

subsets = []
for _ in range(20):
    data_subset = random.sample(data, subset_size)
    subsets.append(data_subset)

# Order each subset
ordered_subsets = [relay_ordering(subset) for subset in subsets]

# Printing the results
for idx, subset in enumerate(ordered_subsets, 1):
    if idx > -1:
        print(f"Subset {idx}: {subset}")