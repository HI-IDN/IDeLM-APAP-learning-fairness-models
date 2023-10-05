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


def write_json(data, filepath, directory=None, indent_level=4, overwrite=False):
    """Write data to JSON file."""
    import os
    import json

    assert isinstance(filepath, str)
    assert isinstance(data, dict)

    if not filepath.endswith('.json'):
        filepath += '.json'

    if directory is not None:
        assert isinstance(directory, str)
        if not os.path.exists(directory):
            os.makedirs(directory)
        filepath = os.path.join(directory, filepath)

    if os.path.exists(filepath) and not overwrite:
        raise FileExistsError(f"File already exists: {filepath}")

    with open(filepath, 'w') as f:
        json.dump(data, f, indent=indent_level)
    print(f"Saved to file: {filepath}")
    return filepath


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


def transpose_dict(dictionary):
    """
    Transpose a dictionary, swapping primary and secondary keys.

    Args:
        dictionary (dict): Dictionary with format:
            {
                "Date1": {"Type1": Value1, "Type2": Value2},
                ...
            }

    Returns:
        dict: Transposed dictionary with format:
            {
                "Type1": [Value1, ...],
                "Type2": [Value2, ...],
                "Order": ["Date1", ...]
            }
    """
    old_keys = list(dictionary.keys())
    new_keys = list(dictionary[old_keys[0]].keys())
    transposed = {
        new_key: [dictionary[old_key][new_key] for old_key in old_keys]
        for new_key in new_keys
    }
    transposed["Order"] = old_keys

    return transposed


def are_dates_separated_by_delta(date1, date2, delta_days=1):
    """
    Check if two dates are separated by a specified delta in days.

    Parameters:
    - date1, date2: These can be either strings in the format 'YYYY-MM-DD' or datetime.date objects.
    - delta_days: The difference in days by which date1 and date2 should be separated.

    Returns:
    - True if the difference between date1 and date2 equals delta_days, False otherwise.
    """
    from datetime import datetime

    # Convert to datetime.date objects if inputs are strings
    if isinstance(date1, str):
        date1 = datetime.strptime(date1, '%Y-%m-%d').date()

    if isinstance(date2, str):
        date2 = datetime.strptime(date2, '%Y-%m-%d').date()

    return abs((date2 - date1).days) == delta_days


def search_for_file(directory, basename):
    """Search for a file in the directory and its subdirectories."""
    import os
    import glob
    search_path = os.path.join(directory, '**', basename)
    files = glob.glob(search_path, recursive=True)
    if not files:
        raise ValueError(f"File for {basename} not found in {directory}.")
    return files[0]
