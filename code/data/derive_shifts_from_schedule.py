import holidays
import warnings

from data.utils import (read_json, write_json, transpose_dict, are_dates_separated_by_delta, search_for_file,
                        is_workday, generate_dates)
import argparse
import re
import os
import datetime
from data.staff import Doctors, ADMIN_IDENTIFIER
from data.schedule import DoctorSchedule


class WeeklySchedule:
    def __init__(self, week_dict, start_date, end_date):
        """Generate a dictionary containing only weekdays."""
        assert isinstance(start_date, datetime.date), f"Invalid start date: {start_date}"
        assert isinstance(end_date, datetime.date), f"Invalid end date: {end_date}"
        assert are_dates_separated_by_delta(start_date, end_date, 6), f"Invalid date range: {start_date} - {end_date}"

        weekend = []
        workday = []
        week = {}
        self.dates = generate_dates(start_date, end_date)
        for date in self.dates:
            name_of_day = self.get_weekday_name(date)
            keys = [key for key in week_dict if key.startswith(name_of_day)]
            if is_holiday(date):
                weekend.extend(keys)
                week[date] = 'Weekend'
            else:
                workday.extend(keys)
                week[date] = 'Weekday'

        self.weekday = workday
        self.weekend = weekend
        self.week = week
        self.values = week_dict

    def get_next_day_type(self, given_date, given_day_type='Weekday'):
        """Get the value of the next day of a given type following a given day, along with the associated values."""
        next_dates = [(date, day_type) for date, day_type in self.week.items() if date > given_date]
        for next_day, day_type in next_dates:
            if day_type == given_day_type:
                day_values = self.get_values(next_day)
                return next_day, day_values
        return None, None  # No next weekday found

    def get_prev_day_type(self, given_date, given_day_type='Weekday'):
        """Get the value of the previous day of a given type before a given day, along with the associated values."""
        prev_dates = [(date, day_type) for date, day_type in self.week.items() if date < given_date]
        for next_day, day_type in reversed(prev_dates):
            if day_type == given_day_type:
                day_values = self.get_values(next_day)
                return next_day, day_values
        return None, None  # No prev weekday found

    def get_weekday_name(self, date):
        """ Get the weekday name (e.g., 'Mon', 'Tue', 'Wed') for a given date."""
        # You might need to adjust the slicing based on your actual keys in 'Values'
        return date.strftime('%a')[:3]

    def get_day_type(self, date):
        """Get the type of day for a given date."""
        return self.week.get(date)

    def get_values(self, date):
        """Get the values for a given date."""
        name = self.get_weekday_name(date)
        values = [(key, values) for key, values in self.values.items() if key.startswith(name)]
        if self.get_day_type(date) == 'Weekday':
            assert len(values) == 1, f"Multiple values found for {date}: {values}"
            return values[0][1]

        if len(values) < 2:
            # TODO: Not sure if this is the best way to handle this case
            if date not in (
                    datetime.date(2019, 7, 4),
                    datetime.date(2019, 12, 25),
                    datetime.date(2020, 7, 3),
                    datetime.date(2018, 12, 24),
                    datetime.date(2018, 12, 25),
                        datetime.date(2021,12,24),
                    datetime.date(2019, 1, 1),
                    datetime.date(2020, 1, 1)):
                assert 1 == 2, f'{date} has only one shift: {values}'
            am_shift = values[0][1]
            pm_shift = values[0][1]
        else:
            am_shift = [value for key, value in values if key.endswith('AM')][0]
            pm_shift = [value for key, value in values if key.endswith('PM')][0]

        return {'AM': am_shift, 'PM': pm_shift}


def get_next_day_type(given_date, this_week, next_week, given_day_type):
    """
    Get the value of the next day of a given type following a given day.

    Parameters:
    - given_date (datetime.date): The date from which to start searching.
    - this_week (dict): A WeeklySchedule object containing the current week's data.
    - next_week (dict): A WeeklySchedule object containing the following week's data.
    - given_day_type (str): The type of day to find (e.g., 'Weekday' or 'Weekend').

    Returns:
    - A tuple containing:
        (1) The value associated with the next weekday following the given date.
        (2) A boolean indicating whether the next weekday is tomorrow.
    """
    # Check the current week first
    next_weekday, values = this_week.get_next_day_type(given_date, given_day_type)
    if next_weekday is None:
        # If no weekday is found in the current week, check the subsequent week
        next_weekday, values = next_week.get_next_day_type(given_date, given_day_type)
        assert next_weekday is not None, f"No {given_day_type} found after {given_date}"

    return values, next_weekday == given_date + datetime.timedelta(days=1)


def get_prev_day_type(given_date, this_week, prev_week, given_day_type):
    """
    Get the value of the previous day of a given type before a given day.

    Parameters:
    - given_date (datetime.date): The date from which to find the next weekday.
    - this_week (dict): A WeeklySchedule object containing the current week's data.
    - prev_week (dict): A WeeklySchedule object containing the previous week's data.
    - given_day_type (str): The type of day to find (e.g., 'Weekday' or 'Weekend').

    Returns:
    - A tuple containing:
        (1) The value associated with the previous weekday before the given date.
        (2) A boolean indicating whether the previous weekday is yesterday.
    """
    # Check the current week first
    prev_weekday, values = this_week.get_prev_day_type(given_date, given_day_type)
    if prev_weekday is None:
        # If no weekday is found in the current week, check the subsequent week
        prev_weekday, values = prev_week.get_prev_day_type(given_date, given_day_type)
        assert prev_weekday is not None, f"No {given_day_type} found before {given_date}"

    return values, prev_weekday == given_date - datetime.timedelta(days=1)


def is_holiday(date):
    """Check if the given date is a holiday in the USA."""
    workday, holiday = is_workday(date)
    if not workday:
        if holiday != 'Weekend':
            print(f"Found a holiday {holiday} on {date} {date.strftime('%a')[:3]}.")
        return True
    else:
        return False


def generate_new_structure(current, before, after, start_date, end_date):
    result = {}
    this_week = WeeklySchedule(current, start_date, end_date)
    prev_week = WeeklySchedule(before, start_date - datetime.timedelta(days=7),
                               start_date - datetime.timedelta(days=1))
    next_week = WeeklySchedule(after, end_date + datetime.timedelta(days=1),
                               end_date + datetime.timedelta(days=7))

    for date in this_week.dates:
        day_type = this_week.get_day_type(date)
        today = this_week.get_values(date)
        if day_type == 'Weekend':
            today = today['PM']

        if today["Admin"] and today["Admin"] > 0:
            admin = [ADMIN_IDENTIFIER for _ in range(today["Admin"])]
        else:
            admin = None

        on_call = today["Call"]["1"]
        on_late = today["Call"]["2"]

        if day_type == 'Weekend':
            # Holiday
            post_call = None
            post_late = None
            post_holiday = None
            pre_call = None
        else:
            # General case: weekday
            next_weekday, is_tomorrow = get_next_day_type(date, this_week, next_week, 'Weekday')
            prev_weekday, is_yesterday = get_prev_day_type(date, this_week, prev_week, 'Weekday')

            if not is_tomorrow:
                next_weekend, _ = get_next_day_type(date, this_week, next_week, 'Weekend')
                pre_call = next_weekend['AM']["Call"]["1"]
            else:
                pre_call = next_weekday["Call"]["1"]

            if not is_yesterday:
                prev_weekend, _ = get_prev_day_type(date, this_week, prev_week, 'Weekend')
                post_call = prev_weekend['PM']["Call"]["1"]
                post_late = prev_weekend['PM']["Call"]["2"]
                post_holiday = prev_weekend['AM']["Call"]["1"]
                if post_holiday == post_call or post_holiday == post_late:
                    post_holiday = None
            else:
                post_call = prev_weekday["Call"]["1"]
                post_late = prev_weekday["Call"]["2"]
                post_holiday = None

            if post_late == pre_call:
                pre_call = None  # Can be an issue immediately after a holiday (e.g. Monday after a long weekend)

        offsite = today["Offsite"]

        weekday_name = this_week.get_weekday_name(date)
        result[weekday_name] = {
            "OnCall": on_call,
            "OnLate": on_late,
            "Post-Call": post_call if post_call not in offsite else None,
            "Post-Holiday": post_holiday if post_holiday not in offsite else None,
            "Post-Late": post_late if post_late not in offsite else None,
            "Pre-Call": pre_call if pre_call not in offsite else None,
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


def find_unassigned(schedule, staff):
    """For each day, find the doctors who are not assigned to any shift, and add them under the key 'Unassigned'."""
    for day in schedule:
        day_type = schedule[day]['Day']
        if day_type == 'Weekend':
            unassigned = list()
        else:
            assigned_doctors = list()
            unassigned = staff.everyone.copy()

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
                if assigned == staff.unknown.ID:
                    Warning(f"An undefined doctor {assigned} is assigned on {day}.")
                    continue

                assert assigned in staff.everyone, f"Doctor '{assigned}' is not in the list of doctors."
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

    start_date = datetime.datetime.strptime(week_range['start'], '%Y-%m-%d').date()
    end_date = datetime.datetime.strptime(week_range['end'], '%Y-%m-%d').date()

    new_structure = generate_new_structure(week_current, week_before, week_after, start_date, end_date)
    doctors = Doctors(start_date=start_date, end_date=end_date)
    new_structure = find_unassigned(new_structure, doctors)
    new_structure = transpose_dict(new_structure)

    new_structure['Doctors'] = doctors.everyone
    new_structure['Period'] = week_range

    filename = args.output
    illegal = filename.replace(".json", "_ILLEGAL.json")
    if os.path.exists(illegal):
        os.remove(illegal)
    err_filename = filename.replace('.json', '.err')
    if os.path.exists(err_filename):
        os.remove(err_filename)

    schedule = DoctorSchedule(new_structure)
    schedule.print()

    # Verify the output structure is valid
    valid, errors = schedule.validate()
    if not valid:
        print("The generated schedule is not valid.")
        # Write errors to the err file
        with open(err_filename, 'w') as err_file:
            for error in errors:
                err_file.write(error + '\n')

        filename = illegal
        print("\n".join(errors))

    write_json(new_structure, filename, overwrite=True, indent_level=None)


if __name__ == "__main__":
    main()
