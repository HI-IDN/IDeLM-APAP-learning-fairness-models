import argparse
import pandas as pd  # Assuming you're using pandas for file reading in your class.
from data.utils import read_json
import datetime
from data.staff import Doctors, ADMIN_IDENTIFIER, CHARGE_IDENTIFIER, CARDIAC_IDENTIFIER

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
        self.everyone = sorted(set().union(*self.working.values()))

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

    def transform_data(self, remove_placeholder=True):
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
        assigment = {
            'Whine': [[self.staff.unknown.ID] * len(self.data['Unassigned'][ix])
                      for ix, day in enumerate(self.data['Order'])],
            'Charge': [self.staff.unknown.ID] * len(self.data['Order']),
            'Cardiac': [self.staff.unknown.ID] * len(self.data['Order'])
        }

        if remove_placeholder:
            for d, day in enumerate(self.data['Order']):
                for turn_order in self.TURN_ORDER:
                    if self.data[turn_order][d] is None:
                        continue
                    if ADMIN_IDENTIFIER in self.data[turn_order][d]:
                        self.data[turn_order][d].remove(ADMIN_IDENTIFIER)
                    if self.staff.unknown.ID in self.data[turn_order][d]:
                        self.data[turn_order][d].remove(self.staff.unknown.ID)

        all_order = []
        all_points = []
        for ix, day in enumerate(self.data['Order']):
            order = []
            points = []
            current_tally = 1
            for turn_order in self.TURN_ORDER:
                items = self.data[turn_order][ix]
                if isinstance(items, list):
                    order.append(items)
                    if turn_order == 'Admin':
                        points.append([ADMIN_POINTS] * len(items))
                    else:
                        points.append(list(range(current_tally, current_tally + len(items))))
                    current_tally += len(items)
                elif items is not None:
                    order.append([items])
                    points.append([current_tally])
                    current_tally += 1
                else:
                    order.append([])
                    points.append([])
            all_order.append(order)
            all_points.append(points)
        return working, offsite, assigment, all_order, all_points

    @property
    def assigned(self):
        """ If a placeholder doctor is found in the schedule, return False. """
        return self.staff.unknown.ID not in self.assigment['Whine'] and \
            self.staff.unknown.ID not in self.assigment['Charge'] and \
            self.staff.unknown.ID not in self.assigment['Cardiac']

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

        def print_nested_list(key, values, t):
            nonlocal output

            max_rows = max(len(item) if item else 0 for item in values)
            if max_rows == 0:
                items_to_print = [key] + [''] * len(self.data['Order']) * 2
                output.append(row_format.format(*items_to_print))

            # Iterate for each row and print
            for row in range(max_rows):
                items_to_print = [key]
                # For each column, get the value if it exists, otherwise use an empty string
                for col in values:
                    if row < len(col) and col[row]:
                        items_to_print.append(apply_color(col[row]))
                    else:
                        items_to_print.append('')
                items_to_print = ([key] +
                                  [apply_color(col[row]) if row < len(col) and col[row] else '' for col in values] +
                                  [self.points[d][t][row] if len(self.points[d][t]) > row and self.points[d][t] else ''
                                   for d, day in enumerate(self.data['Order'])]
                                  )
                output.append(row_format.format(*items_to_print))

        # Define the row format.
        # The first placeholder reserves 10 spaces and the rest reserve 4 spaces each.
        row_format_short = "{:<12}" + "{:>4}" * len(self.data["Order"]) + "  | "
        row_format = row_format_short + "{:>4}" * len(self.data["Order"])
        header = [""] + self.data["Order"] + self.data["Order"]
        header = row_format.format(*header)
        output.append(header)
        separator = '-' * len(header)

        for t, turn_order in enumerate(self.TURN_ORDER):
            if turn_order == "Unassigned":
                output.append(separator)
                if self.assigned:
                    print_nested_list('Assigned', self.assigment['Whine'], t)
                else:
                    print_nested_list(turn_order, self.data[turn_order], t)
            elif turn_order == "Admin":
                output.append(separator)
                print_nested_list(turn_order, self.data[turn_order], t)
            else:
                row = ([turn_order] + [apply_color(item) if item is not None else '' for item in self.data[turn_order]]
                       + [",".join([str(x) for x in self.points[d][t]]) for d, day in enumerate(self.data['Order'])])
                output.append(row_format.format(*row))

        output.append(separator)
        # Print the charge doctors
        charge = [apply_color(item) for item in self.assigment['Charge']]
        row = ['Charge'] + charge
        output.append(row_format_short.format(*row))

        # Print the cardiac doctors
        cardiac = [apply_color(item) for item in self.assigment['Cardiac']]
        row = ['Cardiac'] + cardiac
        output.append(row_format_short.format(*row))

        # Print other daily statistics
        output.append(separator)

        # Print the total number of doctors working per day
        working = [len(self.working[day]) for day in self.data['Order']]
        sums = [sum(sum(turn_list) for turn_list in day_list) for day_list in self.points]
        row = ['Working'] + working + sums
        output.append(row_format.format(*row))

        # Print the total number of doctors offsite per day
        offsite = [len(self.offsite[day]) for day in self.data['Order']]
        row = ['Offsite'] + offsite
        output.append(row_format_short.format(*row))

        # Print the total number of doctors per day
        total = [working[i] + offsite[i] for i in range(len(working))]
        row = ['Total'] + total
        output.append(row_format_short.format(*row))

        return "\n".join(output)

    def print_doctors(self):
        """ Print information per doctor. """
        preassigned_points = {doc: self.get_points_per_doctor(doc, add_assigned=False) for doc in self.everyone}
        points_per_doctor = {doc: self.get_points_per_doctor(doc, add_assigned=True) for doc in self.everyone}
        charge = {doc: sum([c for c in self.assigment['Charge'] if c == doc]) for doc in self.everyone}
        cardiac = {doc: sum([c for c in self.assigment['Cardiac'] if c == doc]) for doc in self.everyone}

        row_format = "{:>10}{:>6}" + "{:>6}" * 4
        header = ["Name", "ID", "Pt0", "Pt", CHARGE_IDENTIFIER, CARDIAC_IDENTIFIER]
        header = row_format.format(*header)
        separator = '-' * len(header)
        output = [header, separator]

        for doc in self.everyone:
            row = [self.staff.get_name(doc), doc,
                   preassigned_points[doc] if preassigned_points[doc] > 0 else '',
                   points_per_doctor[doc] if points_per_doctor[doc] > 0 else '',
                   charge[doc] if charge[doc] > 0 else '',
                   cardiac[doc] if cardiac[doc] > 0 else ''
                   ]
            output.append(row_format.format(*row))
        output.append(separator)

        pre_points = pd.Series([preassigned_points[doc] for doc in self.everyone if preassigned_points[doc] > 0])
        post_points = pd.Series([points_per_doctor[doc] for doc in self.everyone if points_per_doctor[doc] > 0])
        charge = pd.Series([charge[doc] for doc in self.everyone if charge[doc] > 0])
        cardiac = pd.Series([cardiac[doc] for doc in self.everyone if cardiac[doc] > 0])

        row = ['Average', '', round(pre_points.mean(), 1), round(post_points.mean(), 1),
               round(charge.mean(), 1), round(cardiac.mean(), 1)]
        output.append(row_format.format(*row))
        row = ['Median', '', round(pre_points.median(), 1), round(post_points.median(), 1),
               round(charge.median(), 1), round(cardiac.median(), 1)]
        output.append(row_format.format(*row))
        row = ['Min', '', round(pre_points.min(), 1), round(post_points.min(), 1),
               round(charge.min(), 1), round(cardiac.min(), 1)]
        output.append(row_format.format(*row))
        row = ['Max', '', round(pre_points.max(), 1), round(post_points.max(), 1),
               round(charge.max(), 1), round(cardiac.max(), 1)]
        output.append(row_format.format(*row))
        return "\n".join(output)

    def get_points_per_doctor(self, doctor, add_assigned=False):
        """Get the total points per doctor over the entire schedule."""
        tally = 0
        for d, day in enumerate(self.data['Order']):
            for t, turn_order in enumerate(self.TURN_ORDER):
                if turn_order == 'Unassigned' and not add_assigned:
                    continue
                data = self.assigment['Whine'][d] if turn_order == 'Unassigned' \
                                                     and self.assigned else self.data[turn_order][d]
                if data and doctor in data:
                    tally += self.points[d][t][data.index(doctor)]
        return tally


def main():
    parser = argparse.ArgumentParser(
        description="Load doctor's schedule from a file and optionally save output to another file.")
    parser.add_argument('input_filename', type=str, help='Path to the schedule input file.')
    parser.add_argument('--output', '-o', type=str, default=None, dest='output_filename',
                        help='Path to save the schedule output. Optional.')

    args = parser.parse_args()
    schedule = DoctorSchedule(args.input_filename)
    print(schedule.print(color_cardiac=True, color_charge=True))
    print()
    print(schedule.print_doctors())

    if args.output_filename is not None:
        with open(args.output_filename, 'w') as f:
            f.write(schedule.print())


if __name__ == "__main__":
    main()
