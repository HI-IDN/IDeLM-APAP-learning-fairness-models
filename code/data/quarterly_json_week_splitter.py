from collections import OrderedDict
import datetime
import argparse
import os
import math
from utils import read_json, write_json


def split_into_weeks(data):
    """
    Splits data into separate weeks based on the dates.

    Args:
        data (dict): Dictionary representing the schedule with year, month, and day.

    Returns:
        dict: Data split into separate weeks.
    """
    weekly_data = {}

    for year, months in sorted(data.items()):
        for month, days in sorted(months.items()):
            for day, day_data in sorted(days.items()):
                current_date = datetime.date(int(year), month_name_to_number(month), int(day))

                year, week_number = current_date.isocalendar()[0], current_date.isocalendar()[1]
                week_key = f"{year}-week{week_number:02}"
                if week_key not in weekly_data:
                    weekly_data[week_key] = {}

                date_key = current_date.strftime('%Y-%m-%d')
                weekly_data[week_key][date_key] = day_data
    return weekly_data


def save_weekly_data(weekly_data, outdir):
    """
    Saves the weekly data into separate JSON files in the specified directory.

    Args:
        weekly_data (dict): Data split into weeks.
        outdir (str): Directory to save the output JSON files.

    Returns:
        list: List of filenames of the saved JSON files.
    """
    filenames = []
    for week_key in sorted(weekly_data.keys()):
        week_values = OrderedDict(sorted(weekly_data[week_key].items()))
        filename = week_key
        if len(weekly_data) < 7:
            filename += "-partial"
        filename = write_json(week_values, filename, outdir)
        filenames.append(filename)
    return filenames

def month_name_to_number(month_name):
    """
    Converts a month name to its corresponding number.

    Args:
        month_name (str): Name of the month.

    Returns:
        int: Corresponding month number.
    """
    month_dict = {
        'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4,
        'May': 5, 'Jun': 6, 'Jul': 7, 'Aug': 8,
        'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
    }
    return month_dict[month_name]


def combine_weekly_data(files):
    """
    Combines weekly data from files in the specified directory into a single dictionary.

    Args:
        files (list): List of filenames of the weekly data JSON files.

    Returns:
        dict: Combined data.
    """
    combined_data = {}
    for filename in files:
        week_data = read_json(filename)
        for year, months in week_data.items():
            if year not in combined_data:
                combined_data[year] = {}
            for month, days in months.items():
                if month not in combined_data[year]:
                    combined_data[year][month] = {}
                for day, day_data in days.items():
                    combined_data[year][month][day] = day_data
    return combined_data


def flatten_dict(data):
    """
    Flattens a nested dictionary into a single-level dictionary.

    Args:
        data (dict): Nested dictionary with year, month, and day.

    Returns:
        dict: Flattened dictionary with date as the key.
    """
    flattened = {}
    for year, months in data.items():
        for month, days in months.items():
            for day, day_data in days.items():
                key = f"{year}-{month_name_to_number(month):02}-{int(day):02}"
                flattened[key] = day_data
    return flattened


def compare_dicts(dict1, dict2, path=[]):
    """
    Compares two dictionaries and prints the differences, if any.

    Args:
        dict1 (dict): First dictionary to compare.
        dict2 (dict): Second dictionary to compare.
        path (list, optional): List of keys for nested dictionaries. Defaults to an empty list.

    Returns:
        bool: True if the dictionaries match, False otherwise.
    """
    if set(dict1.keys()) != set(dict2.keys()):
        print(f"Keys do not match at path: {' -> '.join(path)}")
        missing_in_dict1 = set(dict2.keys()) - set(dict1.keys())
        missing_in_dict2 = set(dict1.keys()) - set(dict2.keys())
        if missing_in_dict1:
            print(f"Keys present in dict2 but missing in dict1: {missing_in_dict1}")
        if missing_in_dict2:
            print(f"Keys present in dict1 but missing in dict2: {missing_in_dict2}")
        return False

    for key, value1 in dict1.items():
        new_path = path + [key]
        value2 = dict2[key]

        if isinstance(value1, dict) and isinstance(value2, dict):
            if not compare_dicts(value1, value2, new_path):
                return False
        elif value1 != value2:
            # Special case for NaN values
            if isinstance(value1, float) and isinstance(value2, float):
                if math.isnan(value1) and math.isnan(value2):
                    continue

            print(f"Values do not match at path: {' -> '.join(new_path)}")
            print(f"Value in dict1: {value1}")
            print(f"Value in dict2: {value2}")
            return False

    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Split quarterly JSON data into weekly files.')
    parser.add_argument('infile', type=str, help='Path to the input quarterly JSON file.')
    parser.add_argument('--outdir', type=str, required=True, help='Output directory to save the weekly JSON files.')

    args = parser.parse_args()
    data = read_json(args.infile)

    weekly_data = split_into_weeks(data)
    files = save_weekly_data(weekly_data, args.outdir)

    # Verify if combined weekly data matches the original data
    combined_data = combine_weekly_data(files)
    assert compare_dicts(combined_data, flatten_dict(data)), ("Error: Combined weekly data does not match the "
                                                              "original data!")
