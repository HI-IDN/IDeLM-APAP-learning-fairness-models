import argparse
import pandas as pd  # Assuming you're using pandas for file reading in your class.
from data.utils import read_json
import datetime
from data.staff import Doctors, ADMIN_IDENTIFIER

ADMIN_POINTS = 8


class DoctorSchedule:
    TURN_ORDER = [
        'Post-Call',
        'Post-Holiday',
        'Post-Late',
        'Pre-Call',
        'Unassigned',
        'OnLate',
        'OnCall',
        'Admin'
    ]

    def __init__(self, filepath):
        data = read_json(filepath)
        # Extract 'start' and 'end' values and convert to date format
        start_date = datetime.datetime.strptime(data['Period']['start'], '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime(data['Period']['end'], '%Y-%m-%d').date()

        self.staff = Doctors(start_date=start_date, end_date=end_date)
        self.data = data
        self.working, self.offsite, self.assigment, self.order, self.points = self.transform_data()

        # Sanity checks
        missing_shifts = [shift for shift in self.TURN_ORDER if shift not in data]
        assert not missing_shifts, f"Shift {missing_shifts[0]} not found in schedule."
        assert data['Doctors'] == self.staff.everyone, "Doctor list in schedule does not match doctor list in staff.csv"
        for ix, day in enumerate(data['Order']):
            if data['Day'][ix] == 'Weekend':
                continue

            assert len(self.working[day]) == len(set(self.working[day])), f"Duplicate doctors found on {day}"
            assert len(self.offsite[day]) == len(set(self.offsite[day])), f"Duplicate doctors found on {day}"
            assert (self.staff.everyone ==
                    sorted(self.working[day] + self.offsite[day])), f"Missing doctors found on {day}"
            print(f"Day {day} passed sanity checks.")
        print("All days passed sanity checks.\n")

    def transform_data(self):
        def get_offsite_doctors(day):
            """ Returns a list of doctors offsite on a given day. """
            day = self.data['Order'].index(day)
            return [doctor for doctor in self.data['Offsite'][day] if doctor != self.staff.unknown.ID]

        def get_working_doctors(day):
            """ Returns a list of doctors working on a given day. """
            day = self.data['Order'].index(day)
            working = []
            for turn_order in self.TURN_ORDER:
                items = self.data[turn_order][day]
                if isinstance(items, list):
                    working.extend(items)
                else:
                    working.append(items)

            # Remove any placeholder doctors
            return [doctor for doctor in working
                    if doctor != self.staff.unknown.ID
                    and doctor != ADMIN_IDENTIFIER
                    and doctor is not None
                    ]

        working = {day: get_working_doctors(day) for day in self.data['Order']}
        offsite = {day: get_offsite_doctors(day) for day in self.data['Order']}
        assigment = [[self.staff.unknown.ID] * len(self.data['Unassigned'][ix])
                     for ix, day in enumerate(self.data['Order'])]

        all_order = []
        all_points = []
        for ix, day in enumerate(self.data['Order']):
            order = []
            points = []
            for turn_order in self.TURN_ORDER:
                items = self.data[turn_order][ix]
                if isinstance(items, list):
                    order.extend(items)
                    points.extend([turn_order] * len(items))
                else:
                    order.append(items)
                    points.append(turn_order)
            all_order.append(order)
            all_points.append(points)

        return working, offsite, assigment, all_order, all_points

    @property
    def assigned(self):
        """ If a placeholder doctor is found in the schedule, return False. """
        return self.staff.unknown.ID not in self.assigment

    def print(self, color_cardiac=False, color_charge=False):
        output = []

        def apply_color(doctor):
            default_color = '\033[0m'  # Default

            def get_color(doctor):
                if doctor in self.staff.charge_doctors and doctor in self.staff.cardiac_doctors and color_cardiac and color_charge:
                    return '\033[95m'  # Purple
                if doctor in self.staff.charge_doctors and color_charge:
                    return '\033[94m'  # Blue
                if doctor in self.staff.cardiac_doctors and color_cardiac:
                    return '\033[91m'  # Red
                return default_color

            color = get_color(doctor)
            doctor = '__' if doctor not in self.staff.everyone else doctor
            if color == default_color:
                return doctor
            item = color + doctor + default_color
            return f"  {item}"

        def print_nested_list(key, values):
            nonlocal output
            max_rows = max(len(item) for item in values)
            # Iterate for each row and print
            for row in range(max_rows):
                items_to_print = [key]
                # For each column, get the value if it exists, otherwise use an empty string
                for col in values:
                    if row < len(col) and col[row]:
                        items_to_print.append(apply_color(col[row]))
                    else:
                        items_to_print.append('')

                output.append(row_format.format(*items_to_print))

        # Define the row format.
        # The first placeholder reserves 10 spaces and the rest reserve 4 spaces each.
        row_format = "{:<12}" + "{:>4}" * len(self.data["Order"])
        header = [""] + self.data["Order"]
        header = row_format.format(*header)
        output.append(header)
        separator = '-' * len(header)

        for turn_order in self.TURN_ORDER:
            if turn_order == "Unassigned":
                output.append(separator)
                if not self.assigned:
                    print_nested_list('Assigned', self.assigment)
                else:
                    print_nested_list(turn_order, self.data[turn_order])
            elif turn_order == "Admin":
                output.append(separator)
                print_nested_list(turn_order, self.data[turn_order])
                output.append(separator)
            else:
                row = [turn_order] + [apply_color(item) if item is not None else ''
                                      for item in self.data[turn_order]]
                output.append(row_format.format(*row))

        output.append(separator)
        working = [len(self.working[day]) for day in self.data['Order']]
        row = ['Working'] + working
        output.append(row_format.format(*row))
        offsite = [len(self.offsite[day]) for day in self.data['Order']]
        row = ['Offsite'] + offsite
        output.append(row_format.format(*row))
        total = [working[i] + offsite[i] for i in range(len(working))]
        row = ['Total'] + total
        output.append(row_format.format(*row))
        return "\n".join(output)


def main():
    parser = argparse.ArgumentParser(
        description="Load doctor's schedule from a file and optionally save output to another file.")
    parser.add_argument('input_filename', type=str, help='Path to the schedule input file.')
    parser.add_argument('--output', '-o', type=str, default=None, dest='output_filename',
                        help='Path to save the schedule output. Optional.')

    args = parser.parse_args()
    schedule = DoctorSchedule(args.input_filename)
    print(schedule.print(color_cardiac=True, color_charge=True))
    if args.output_filename is not None:
        with open(args.output_filename, 'w') as f:
            f.write(schedule.print())


if __name__ == "__main__":
    main()
