from collections import OrderedDict
import datetime
import argparse
import json
import os
import math

def split_into_weeks(data):
    """
    Splits the data into separate weeks

    :param data: The JSON data representing the schedule.
    :param weekly_data: The JSON data representing the schedule split into weeks.
    """
    weekly_data = {}

    for year, months in sorted(data.items()):
        for month, days in sorted(months.items()):
            for day, day_data in sorted(days.items()):
                current_date = datetime.date(int(year), month_name_to_number(month), int(day))

                week_key = f"{current_date.isocalendar()[0]}-week{current_date.isocalendar()[1]}"
                if week_key not in weekly_data:
                    weekly_data[week_key] = {}

                date_key = current_date.strftime('%Y-%m-%d')
                weekly_data[week_key][date_key] = day_data
    return weekly_data

def save_weekly_data(weekly_data, outdir):
    """Saves the weekly data to separate JSON files."""
    for week_key in sorted(weekly_data.keys()):
        week_values = OrderedDict(sorted(weekly_data[week_key].items()))
        save_to_file(week_values, week_key, outdir)


def month_name_to_number(month_name):
    """Helper function to convert month name to month number."""
    month_dict = {
        'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4,
        'May': 5, 'Jun': 6, 'Jul': 7, 'Aug': 8,
        'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
    }
    return month_dict[month_name]


def save_to_file(data, filename, outdir):
    """Helper function to save data to JSON file."""
    if not os.path.exists(outdir):
        os.makedirs(outdir)

    if len(data)<7:
        filename += "-partial"

    full_path = os.path.join(outdir, f"{filename}.json")
    with open(full_path, 'w') as f:
        json.dump(data, f, indent=4)
    print(f"Saved to file: {full_path}")


def combine_weekly_data(outdir):
    combined_data = {}
    for filename in sorted(os.listdir(outdir)):
        with open(os.path.join(outdir, filename), 'r') as f:
            week_data = json.load(f)
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
    Flattens a nested dictionary structure with year, month, and day into a single-level dictionary.

    :param data: The nested dictionary to flatten.
    :return: A flattened dictionary.
    """
    flattened = {}
    for year, months in data.items():
        for month, days in months.items():
            for day, day_data in days.items():
                key = f"{year}-{month_name_to_number(month):02}-{int(day):02}"
                flattened[key] = day_data
    return flattened

def compare_dicts(dict1, dict2, path=[]):
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

    with open(args.infile, 'r') as f:
        data = json.load(f)

    weekly_data = split_into_weeks(data)
    save_weekly_data(weekly_data, args.outdir)

    # Verify if combined weekly data matches the original data
    combined_data = combine_weekly_data(args.outdir)
    assert compare_dicts(combined_data, flatten_dict(data)), ("Error: Combined weekly data does not match the "
                                                              "original data!")
