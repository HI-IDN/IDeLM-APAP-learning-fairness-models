from utils import read_json, write_json, read_and_remove_file
from utils import transpose_dict
from utils import are_dates_separated_by_delta
from utils import search_for_file
import argparse
import re
import os
import datetime
from staff import Doctors, ADMIN_IDENTIFIER

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


def get_previous_weekend_shifts(current_day, current_week_dict, previous_week_dict):
    """
    Get the AM and PM shifts of the previous day before a given day.

    Parameters:
    - current_day (str): The day of the week for which the previous day's shifts are to be found.
    - current_week_dict (dict): Dictionary containing the current week's data.
    - previous_week_dict (dict): Dictionary containing the prior week's data.

    Returns:
    - tuple: AM and PM shifts for the day before the current_day.
    """
    yesterday = WEEK[(WEEK.index(current_day) - 1) % 7]

    am_key = f"{yesterday} AM"
    pm_key = f"{yesterday} PM"

    # If yesterday was in the current week
    if yesterday in WEEK[:WEEK.index(current_day)]:
        assert am_key in current_week_dict, f"AM shift not found for {yesterday} in current week"
        assert pm_key in current_week_dict, f"PM shift not found for {yesterday} in current week"
        return current_week_dict.get(am_key), current_week_dict.get(pm_key)
    # If yesterday was in the previous week
    else:
        assert am_key in previous_week_dict, f"AM shift not found for {yesterday} in previous week"
        assert pm_key in previous_week_dict, f"PM shift not found for {yesterday} in previous week"
        return previous_week_dict.get(am_key), previous_week_dict.get(pm_key)


def get_next_weekend_shifts(current_day, current_week_dict, next_week_dict):
    """
    Get the AM and PM shifts for the next day after a given day.

    Parameters:
    - current_day (str): The day of the week for which the following day's shifts are to be found.
    - current_week_dict (dict): Dictionary containing the current week's data.
    - next_week_dict (dict): Dictionary containing the next week's data.

    Returns:
    - tuple: AM and PM shifts for the day following the current_day.
    """
    assert current_day in WEEK, f"Invalid day of the week: {current_day}. Must be one of {WEEK}"
    tomorrow = WEEK[(WEEK.index(current_day) + 1) % 7]

    am_key = f"{tomorrow} AM"
    pm_key = f"{tomorrow} PM"

    # If the next day is in the same week as current_day
    if tomorrow in WEEK[:WEEK.index(current_day) + 2]:
        assert am_key in current_week_dict, f"AM shift not found for {tomorrow} in current week"
        assert pm_key in current_week_dict, f"PM shift not found for {tomorrow} in current week"
        return current_week_dict.get(am_key), current_week_dict.get(pm_key)

    # If the next day is in the next week
    else:
        assert am_key in next_week_dict, f"AM shift not found for {tomorrow} in next week"
        assert pm_key in next_week_dict, f"PM shift not found for {tomorrow} in next week"
        return next_week_dict.get(am_key), next_week_dict.get(pm_key)


def get_next_shift(current_day, current_week_dict, next_week_dict):
    """
    Get the next shift following a given day.

    Parameters:
    - current_day (str): The day of the week for which the following day's shifts are to be found.
    - current_week_dict (dict): Dictionary containing the current week's data.
    - next_week_dict (dict): Dictionary containing the next week's data.

    Returns:
    - dict: Value of the next shift following the current_day.
    """
    return next((current_week_dict[shift] for shift in current_week_dict if shift > current_day),
                next_week_dict[next(iter(next_week_dict))])


def generate_new_structure(current, before, after):
    result = {}
    days = list(current.keys())
    weekdays = generate_weekdays(current)
    weekdays_before = generate_weekdays(before)
    weekdays_after = generate_weekdays(after)

    for index, today in enumerate(days):
        day_type = 'Weekday' if today in weekdays else 'Weekend'
        if current[today]["Admin"] and current[today]["Admin"] > 0:
            admin = [ADMIN_IDENTIFIER for _ in range(current[today]["Admin"])]
        else:
            admin = None

        on_call = current[today]["Call"]["1"]
        on_late = current[today]["Call"]["2"]

        if 'AM' in today:
            # Ignore the AM shifts
            continue
        elif 'PM' in today:
            next_day = get_next_shift(today, current, after)
            post_call = None
            post_late = None
            post_holiday = None
            pre_call = next_day["Call"]["1"]
        else:
            # General case: weekday
            next_weekday, is_tomorrow = get_next_weekday(today, current, after, weekdays, weekdays_after)
            prev_weekday, is_yesterday = get_previous_weekday(today, current, before, weekdays, weekdays_before)

            if not is_tomorrow:
                am_shift, pm_shift = get_next_weekend_shifts(today, current, after)
                pre_call = am_shift["Call"]["1"]
            else:
                pre_call = next_weekday["Call"]["1"]

            if not is_yesterday:
                am_shift, pm_shift = get_previous_weekend_shifts(today, current, before)
                post_call = pm_shift["Call"]["1"]
                post_late = pm_shift["Call"]["2"]
                post_holiday = am_shift["Call"]["1"]
            else:
                post_call = prev_weekday["Call"]["1"]
                post_late = prev_weekday["Call"]["2"]
                post_holiday = None

        offsite = current[today]["Offsite"]

        today = today.split(' ')[0]  # Remove the AM/PM suffix if present
        result[today] = {
            "OnCall": on_call,
            "OnLate": on_late,
            "Post-Call": post_call,
            "Post-Holiday": post_holiday,
            "Post-Late": post_late,
            "Pre-Call": pre_call,
            "Admin": admin,
            "Offsite": offsite,
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


def find_unassigned(schedule, doctors):
    """For each day, find the doctors who are not assigned to any shift, and add them under the key 'Unassigned'."""
    for day in schedule:
        day_type = schedule[day]['Day']
        if day_type == 'Weekend':
            unassigned = list()
        else:
            assigned_doctors = list()
            unassigned = doctors.everyone.copy()

            for shift, values in schedule[day].items():
                if shift == 'Day':
                    continue

                if not isinstance(values, list):
                    values = [values]
                assigned_doctors.extend(values)

            assigned_doctors = list(set(assigned_doctors))

            for assigned in assigned_doctors:
                if assigned is None:
                    continue
                if assigned == ADMIN_IDENTIFIER:
                    continue
                if assigned == doctors.unknown.ID:
                    Warning(f"An undefined doctor {assigned} is assigned on {day}.")
                    continue

                assert assigned in doctors.everyone, f"Doctor '{assigned}' is not in the list of doctors."
                unassigned.remove(assigned)

        schedule[day]['Unassigned'] = unassigned

    return schedule


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
    doctors = Doctors(start_date=datetime.datetime.strptime(week_range['start'], '%Y-%m-%d').date(),
                      end_date=datetime.datetime.strptime(week_range['end'], '%Y-%m-%d').date())
    new_structure = find_unassigned(new_structure, doctors)
    new_structure = transpose_dict(new_structure)

    new_structure['Doctors'] = doctors.everyone
    new_structure['Period'] = week_range

    write_json(new_structure, os.path.basename(args.output), os.path.dirname(args.output), indent_level=None)


if __name__ == "__main__":
    main()
