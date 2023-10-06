from utils import read_json, write_json, read_and_remove_file
from utils import transpose_dict
from utils import are_dates_separated_by_delta
from utils import search_for_file
import argparse
import re
import os
import datetime

WEEK = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
WEEKDAYS = WEEK[:5]
WEEKEND = [f"{day} AM" for day in WEEK] + [f"{day} PM" for day in WEEK]


def generate_weekdays(week_dict):
    """Generate a dictionary containing only weekdays."""
    return [day for day in week_dict if day in WEEKDAYS]


def get_next_weekday(current_day, current_week_dict, next_week_dict, weekdays, weekdays_after):
    """
    Get the value of the next weekday following a given day.

    Parameters:
    - current_day (str): The day of the week for which the next weekday value is to be found.
    - current_week_dict (dict): Dictionary containing the current week's data.
    - next_week_dict (dict): Dictionary containing the subsequent week's data.
    - weekdays (list): List of weekdays in the current week.
    - weekdays_after (list): List of weekdays in the subsequent week.

    Returns:
    - dict: The value associated with the next weekday following the current_day.
            If not found in current_week_dict, it looks in next_week_dict.
            If no weekday is found, returns None.
    - bool: True if the next weekday is tomorrow, False otherwise.
    """
    found_next_weekday = None
    tomorrow = WEEK[(WEEK.index(current_day) + 1) % 7]

    # Check weekdays after the current day in the same week
    for day in weekdays[weekdays.index(current_day) + 1:]:
        if day in current_week_dict:
            found_next_weekday = day
            return current_week_dict[found_next_weekday], day == tomorrow

    # If not found, get the first weekday from the next week
    for day in weekdays_after:
        if day in next_week_dict:
            found_next_weekday = day
            return next_week_dict[found_next_weekday], False

    # No next weekday found
    assert found_next_weekday is not None, f"No next weekday found for {current_day}"
    return None  # In case no next weekday is found


def get_previous_weekday(current_day, current_week_dict, previous_week_dict, weekdays, weekdays_before):
    """
    Get the value of the previous weekday before a given day.

    Parameters:
    - current_day (str): The day of the week for which the previous weekday value is to be found.
    - current_week_dict (dict): Dictionary containing the current week's data.
    - previous_week_dict (dict): Dictionary containing the prior week's data.
    - weekdays (list): List of weekdays in the current week.
    - weekdays_before (list): List of weekdays in the previous week.

    Returns:
    - dict: The value associated with the weekday preceding the current_day.
            If not found in current_week_dict, it looks in previous_week_dict.
            If no weekday is found, returns None.
    - bool: True if the previous weekday is yesterday, False otherwise.
    """
    found_previous_day = None
    yesterday = WEEK[(WEEK.index(current_day) - 1) % 7]

    # Check weekdays before the current day in the same week
    for day in reversed(weekdays[:weekdays.index(current_day)]):
        if day in current_week_dict:
            found_previous_day = day
            return current_week_dict[found_previous_day], day == yesterday

    # If not found, get the last weekday from the previous week
    weekdays_before = reversed(weekdays_before)
    for day in weekdays_before:
        if day in previous_week_dict:
            found_previous_day = day
            return previous_week_dict[found_previous_day], False

    # No previous weekday found
    assert found_previous_day is not None, f"No previous weekday found for {current_day}"
    return None, None  # In case no previous weekday is found


def generate_new_structure(current, before, after):
    result = {}
    days = list(current.keys())
    weekdays = generate_weekdays(current)
    weekdays_before = generate_weekdays(before)
    weekdays_after = generate_weekdays(after)

    for index, today in enumerate(days):
        day_type = 'Weekday' if today in weekdays else 'Weekend'

        if day_type == 'Weekend':
            # TODO: handle weekend shifts (e.g. 'Sat AM', 'Sat PM', 'Sun AM', 'Sun PM') later
            continue

        next_day, is_tomorrow = get_next_weekday(today, current, after, weekdays, weekdays_after)
        prev_day, is_yesterday = get_previous_weekday(today, current, before, weekdays, weekdays_before)

        on_call = current[today]["Call"]["1"]
        on_late = current[today]["Call"]["2"]
        admin = [None] * current[today]["Admin"]

        pre_call = next_day["Call"]["1"]
        pre_late = next_day["Call"]["2"]

        post_call = prev_day["Call"]["1"]
        post_late = prev_day["Call"]["2"]

        if not is_yesterday:
            post_holiday = 'X'
        else:
            post_holiday = None

        result[today] = {
            "OnCall": on_call,
            "OnLate": on_late,
            "Admin": admin,
            "Post-Call": post_call,
            "Post-Holiday": post_holiday,
            "Post-Late": post_late,
            "Pre-Call": pre_call,
            "Pre-Late": pre_late,
            "Day": day_type
        }

    return result


def generate_week_range(week):
    """Generate a string representing the week range."""
    start_date = list(week.keys())[0]
    end_date = list(week.keys())[-1]
    return {'start': start_date, 'end': end_date}


def verify_and_flatten_weeks(week_before, week_current, week_after):
    """
    Verify the continuity of the weeks, flatten their structure, and
    return the start and end dates of the current week.

    Parameters:
    - week_before: Dictionary representing the previous week's data.
    - week_current: Dictionary representing the current week's data.
    - week_after: Dictionary representing the following week's data.

    Returns:
    - A dictionary containing the flattened weeks.
    """

    # Extract start and end dates
    current = generate_week_range(week_current)
    before = generate_week_range(week_before)
    after = generate_week_range(week_after)

    assert are_dates_separated_by_delta(before['end'], current['start'], 1)
    assert are_dates_separated_by_delta(current['end'], after['start'], 1)

    # Flatten the weeks
    flattened_current = flatten_week(week_current)
    flattened_before = flatten_week(week_before)
    flattened_after = flatten_week(week_after)

    return flattened_before, flattened_current, flattened_after


def flatten_week(week):
    """ Flatten the week structure to a single dictionary """
    result = {}
    for date in week:
        for shift in week[date]:
            result[shift] = week[date][shift]

    return result


def extract_year_and_week(file_path):
    """Extract the year and week number from the file name."""
    base_filename = os.path.basename(file_path)
    pattern = r"^(\d{4})-week(\d{1,2})\.json$"
    match = re.match(pattern, base_filename)
    if match:
        year = int(match.group(1))
        week_number = int(match.group(2))
        return year, week_number
    else:
        return None, None


def get_year_week_pattern(date, delta_days):
    """ Convert a date to the YYYY-week%d pattern. """
    if not isinstance(date, datetime.date):
        date = datetime.datetime.strptime(date, '%Y-%m-%d').date()
    if delta_days != 0:
        date += datetime.timedelta(days=delta_days)
    year_number, week_number = date.isocalendar()[0], date.isocalendar()[1]
    return f"{year_number}-week{week_number:02}"


def valid_filename(file_path):
    """File must be a JSON file and match the expected pattern."""
    if not isinstance(file_path, str):
        raise argparse.ArgumentTypeError(f"File path must be a string: {file_path}")

    year, week_number = extract_year_and_week(file_path)
    if year is None or week_number is None:
        raise argparse.ArgumentTypeError(f"File name does not match the expected format (YYYY-week%d.json): "
                                         f"{file_path}")

    return file_path


def main():
    parser = argparse.ArgumentParser(description="Process weekly JSON data and generate new structure.")

    # Input file
    parser.add_argument('-i', '--input', type=valid_filename, required=True,
                        help='Input file containing weekly schedule data. Must match the format YYYY-week%d.json')

    # Output file
    parser.add_argument('-o', '--output', type=valid_filename, required=True,
                        help='Output file to save processed schedule.')

    args = parser.parse_args()

    # Get the current week's data
    week_current = read_json(args.input)
    week_range = generate_week_range(week_current)

    # Get the previous and next week's data
    input_dir = os.path.dirname(args.input)
    week_before_path = search_for_file(input_dir, f"{get_year_week_pattern(week_range['start'], -1)}.json")
    week_after_path = search_for_file(input_dir, f"{get_year_week_pattern(week_range['end'], 1)}.json")

    week_before = read_json(week_before_path)
    week_after = read_json(week_after_path)

    week_before, week_current, week_after = verify_and_flatten_weeks(week_before, week_current, week_after)

    new_structure = generate_new_structure(week_current, week_before, week_after)
    new_structure = transpose_dict(new_structure)
    new_structure['Period'] = week_range

    write_json(new_structure, os.path.basename(args.output), os.path.dirname(args.output), indent_level=4)


if __name__ == "__main__":
    main()
