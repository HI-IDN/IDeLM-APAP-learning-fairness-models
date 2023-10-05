from utils import read_json, write_json, read_and_remove_file
from utils import transpose_dict
from utils import are_dates_separated_by_delta
from utils import search_for_file
import argparse
import re
import os

WEEK = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
WEEKDAYS = WEEK[:5]
WEEKEND = [f"{day} AM" for day in WEEK] + [f"{day} PM" for day in WEEK]


def generate_weekdays(week_dict):
    """Generate a dictionary containing only weekdays."""
    return [day for day in week_dict if day in WEEKDAYS]


def generate_new_structure(current, before, after):
    result = {}
    days = list(current.keys())
    weekdays = generate_weekdays(current)
    weekdays_before = generate_weekdays(before)
    weekdays_after = generate_weekdays(after)
    debug = False
    for index, today in enumerate(days):
        day_type = 'Weekday' if today in weekdays else 'Weekend'

        if day_type == 'Weekend':
            # TODO: handle weekend shifts (e.g. 'Sat AM', 'Sat PM', 'Sun AM', 'Sun PM') later
            continue

        tomorrow = days[index + 1] if index < len(days) - 1 else None
        yesterday = days[index - 1] if index > 0 else None

        on_call = current[today]["Call"]["1"]
        on_late = current[today]["Call"]["2"]
        admin = [None] * current[today]["Admin"]

        # for the last day, take the first day of 'after' week
        if not tomorrow or today == weekdays[-1]:
            pre_call = after[weekdays_after[0]]["Call"]["1"]
            pre_late = after[weekdays_after[0]]["Call"]["2"]
            if today != 'Fri':
                debug = True
                print(f'CHECK LAST DAY {today}')
        else:
            pre_call = current[tomorrow]["Call"]["1"]
            pre_late = current[tomorrow]["Call"]["2"]

        # for the first day, take the last day of 'before' week
        if not yesterday or today == weekdays[0]:
            post_call = before[weekdays_before[-1]]["Call"]["1"]
            post_late = before[weekdays_before[-1]]["Call"]["2"]
            post_holiday = 'X'
            if today != 'Mon' and today != 'Tue':
                debug = True
                print(f'CHECK FIRST DAY {today}')
        else:
            post_call = current[yesterday]["Call"]["1"]
            post_late = current[yesterday]["Call"]["2"]
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

    if debug:
        for day in before:
            if day in WEEKDAYS:
                print(day, before[day])
        print('---')
        for day in result:
            print(day, result[day])
        print('---')
        for day in after:
            if day in WEEKDAYS:
                print(day, after[day])

    assert debug == False

    return result


def verify_and_flatten_weeks(week_before, week_current, week_after):
    """
    Verify the continuity of the weeks, flatten their structure, and
    return the start and end dates of the current week.

    Parameters:
    - week_before: Dictionary representing the previous week's data.
    - week_current: Dictionary representing the current week's data.
    - week_after: Dictionary representing the following week's data.

    Returns:
    - A dictionary containing the flattened weeks and the start and end dates of the current week.
    """

    # Extract start and end dates
    start_date = list(week_current.keys())[0]
    end_date = list(week_current.keys())[-1]
    next_start_date = list(week_after.keys())[0]
    prev_end_date = list(week_before.keys())[-1]

    assert are_dates_separated_by_delta(prev_end_date, start_date, 1)
    assert are_dates_separated_by_delta(end_date, next_start_date, 1)

    # Flatten the weeks
    flattened_current = flatten_week(week_current)
    flattened_before = flatten_week(week_before)
    flattened_after = flatten_week(week_after)

    return flattened_before, flattened_current, flattened_after, {'start': start_date, 'end': end_date}


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

    # Extract year and week number
    year, week_number = extract_year_and_week(args.input)

    # Construct file paths
    week_current_path = args.input
    input_dir = os.path.dirname(args.input)
    week_before_path = search_for_file(input_dir, f'{year}-week{week_number - 1}.json')
    week_after_path = search_for_file(input_dir, f'{year}-week{week_number + 1}.json')

    week_current = read_json(week_current_path)
    week_before = read_json(week_before_path)
    week_after = read_json(week_after_path)

    week_before, week_current, week_after, week_range = verify_and_flatten_weeks(week_before, week_current, week_after)

    new_structure = generate_new_structure(week_current, week_before, week_after)
    new_structure = transpose_dict(new_structure)
    new_structure['Period'] = week_range

    write_json(new_structure, os.path.basename(args.output), os.path.dirname(args.output), indent_level=None)


if __name__ == "__main__":
    main()
