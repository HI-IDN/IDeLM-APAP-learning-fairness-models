def read_json(filepath):
    """Reads a JSON file and returns a dictionary."""
    import json
    with open(filepath, 'r') as f:
        return json.load(f)

def read_csv(filepath):
    """Reads a CSV file and returns a list of lists."""
    import csv
    with open(filepath, 'r') as f:
        return list(csv.reader(f))