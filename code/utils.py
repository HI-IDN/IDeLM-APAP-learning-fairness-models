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


def read_and_remove_file(filepath):
    """Reads a file and removes it."""
    import os
    with open(filepath, 'r') as f:
        content = f.read()
    os.remove(filepath)
    return content


def extract_values_from_text(text, values):
    """ Extracts values from a text. """
    import re
    return [value for value in values if re.search(r'\b' + value + r'\b', text)]
