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
        filepath = os.path.join(directory, filepath)
    else:
        directory = os.path.dirname(filepath)

    if not os.path.exists(directory):
        os.makedirs(directory)

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


def holidays_that_year(year):
    from datetime import datetime, timedelta

    def memorial_day_weekend():
        last_day_of_may = datetime(year, 5, 31)  # May 31st
        days_to_subtract = last_day_of_may.weekday()  # weekday() returns 0 for Monday
        end = last_day_of_may - timedelta(days=days_to_subtract)
        start = end - timedelta(days=2)  # from Saturday to Monday
        return start, end

    def labor_day_weekend():
        first = datetime(year, 9, 1)  # September 1st
        day_of_week = first.weekday()  # Monday is 0, Sunday is 6
        days_to_add = (7 - day_of_week) % 7
        first_monday_of_september = 1 + days_to_add
        end = datetime(year, 9, first_monday_of_september)
        start = datetime(year, 9, first_monday_of_september) - timedelta(days=2)  # from Saturday to Monday
        return start, end

    def thanksgiving_weekend():
        first = datetime(year, 11, 1)  # November 1st
        day_of_week = first.weekday()  # Monday is 0, Sunday is 6
        fourth_thursday_of_november = 22 + (3 - day_of_week) % 7
        start = datetime(year, 11, fourth_thursday_of_november)
        end = start + timedelta(days=3)  # from Thursday to Sunday
        return start, end

    def fixed_date_holidays(holiday):
        # Check the day of the week
        day_of_week = holiday.weekday()

        # Tuesday to Thursday: No change, holiday is just one day
        if day_of_week in range(1, 4):
            start = holiday
            end = holiday

        # Monday: Long weekend from Saturday to Monday
        elif day_of_week == 0:
            start = holiday - timedelta(days=2)
            end = holiday

        # Friday: Long weekend from Friday to Sunday
        elif day_of_week == 4:
            start = holiday
            end = holiday + timedelta(days=2)

        # Saturday: Observed holiday on Friday, weekend is Friday to Sunday
        elif day_of_week == 5:
            start = holiday - timedelta(days=1)
            end = holiday + timedelta(days=1)

        # Sunday: Long weekend from Saturday to Monday (observed holiday)
        elif day_of_week == 6:
            start = holiday - timedelta(days=1)
            end = holiday + timedelta(days=1)

        return start, end

    def independence_day_weekend():
        # Independence Day is always on July 4th
        independence_day = datetime(year, 7, 4)
        return fixed_date_holidays(independence_day)

    def christmas_weekend():
        christmas = datetime(year, 12, 25)
        return fixed_date_holidays(christmas)

    def new_year_weekend():
        new_years_day = datetime(year, 1, 1)
        return fixed_date_holidays(new_years_day)

    # Define the holidays
    holidays = {
        "New Years": new_year_weekend(),
        "Memorial Day": memorial_day_weekend(),
        "Independence Day": independence_day_weekend(),
        "Labor Day": labor_day_weekend(),
        "Thanksgiving": thanksgiving_weekend(),
        "Christmas": christmas_weekend(),
    }
    holidays = {key: generate_dates(start.date(), end.date()) for key, (start, end) in holidays.items()}

    return holidays


def custom_holidays(input_date):
    """ Get the list of US holidays for the given year. """
    import datetime

    special_holidays = {}
    special = read_csv('../data/special_holidays.csv')
    for date_str, holiday_name in special[1:]:
        date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        if date.year == input_date.year:
            special_holidays[date] = holiday_name

    holidays = holidays_that_year(input_date.year)
    # convert to a dictionary of {date: holiday_name}
    holidays = {date: holiday_name for holiday_name, dates in holidays.items() for date in dates}
    # append any special holidays that are not already in the list
    holidays = {**holidays, **special_holidays}
    return holidays


def is_workday(input_date):
    """ Check if the given date is a workday. Assumes that known US holidays are not workdays. """
    import datetime

    assert isinstance(input_date, datetime.date)

    # Check if the date is a public holiday in the USA
    holidays = custom_holidays(input_date)
    if input_date in holidays:
        return False, holidays[input_date]

    # Check if the date is a weekend
    if input_date.weekday() >= 5:  # 5 and 6 correspond to Saturday and Sunday respectively
        return False, None

    # If it's neither weekend nor a public holiday
    return True, None


def generate_dates(start, end):
    """ Generate a list of dates within the given range. """
    import datetime as dt
    if isinstance(start, str):
        start = dt.datetime.strptime(start, '%Y-%m-%d').date()
    else:
        assert isinstance(start, dt.date)
    if isinstance(end, str):
        end = dt.datetime.strptime(end, '%Y-%m-%d').date()
    else:
        assert isinstance(end, dt.date)

    if start == end:
        return [start]

    return [(start + dt.timedelta(days=i)) for i in range((end - start).days + 1)]

def get_weekday_name(date):
    """ Get the weekday name (e.g., 'Mon', 'Tue', 'Wed') for a given date."""
    return date.strftime('%a')[:3]