import argparse
import pandas as pd  # Assuming you're using pandas for file reading in your class.
from data.utils import read_json
import datetime
from data.staff import Doctors, ADMIN_IDENTIFIER, CHARGE_IDENTIFIER, CARDIAC_IDENTIFIER

ADMIN_POINTS = 8


class Assignment:
    def __init__(self, doctor, points=-1, shift='Unassigned'):
        assert doctor is None or isinstance(doctor, str), f"Doctor must be a string. Got {type(doctor)} instead."
        self.doctor = doctor
        self.points = points
        self.shift = shift

    @property
    def assigned(self):
        return self.shift != 'Unassigned'

    def __repr__(self):
        return f"Assignment('{self.doctor}',{self.points},'{self.shift}')"


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
        rawdata = read_json(filepath)
        # Extract 'start' and 'end' values and convert to date format
        start_date = datetime.datetime.strptime(rawdata['Period']['start'], '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime(rawdata['Period']['end'], '%Y-%m-%d').date()

        self.staff = Doctors(start_date=start_date, end_date=end_date)
        self.rawdata = rawdata
        self.Whine = {day: rawdata['Unassigned'][i] for i, day in enumerate(self.days)}

        self.working, self.offsite, self.assignments = self.transform_rawdata(rawdata)
        self.doctors = sorted(set().union(*self.working.values()))

        self.call_and_late_call_doctors = {day: [rawdata['OnCall'][i], rawdata['OnLate'][i]]
                                           for i, day in enumerate(self.days)}

        self.preassigned = {day: {} for day in self.days}
        for turn_order in self.TURN_ORDER:
            if turn_order == 'Unassigned' or turn_order == 'Admin':
                continue
            for d, day in enumerate(self.days):
                for assignment in self.assignments[turn_order][day]:
                    assert assignment.points not in self.preassigned[day], f'Duplicate points found on {day}'
                    self.preassigned[day][assignment.points] = assignment.doctor

        # Potential charge doctors must be working on the day and capable of being in charge
        self.potential_charge_doctors = {
            day: list(set(self.call_and_late_call_doctors[day]).union(self.Whine[day])
                      & set(self.staff.charge_doctors))
            for day in self.days
        }

        # Potential cardiac doctors must be working as either call or late call, and capable of being cardiac
        self.potential_cardiac_doctors = {
            day: list(set(self.call_and_late_call_doctors[day])
                      & set(self.staff.cardiac_doctors))
            for d, day in enumerate(self.days)
        }

        self.solution = {
            'Whine': {day: [Assignment(self.staff.unknown.ID, list(a.points)[i]) for i, a in
                            enumerate(self.assignments['Unassigned'][day])] for day in self.days},
            'Charge': {day: self.staff.unknown.ID for day in self.days},
            'Cardiac': {day: self.staff.unknown.ID for day in self.days},
            'Points': {doc: None for doc in self.doctors},
            'Target': None
        }

        # Sanity checks
        missing_shifts = [shift for shift in self.TURN_ORDER if shift not in rawdata]
        assert not missing_shifts, f"Shift {missing_shifts[0]} not found in schedule."
        assert rawdata['Doctors'] == self.staff.everyone, ("Doctor list in schedule does not match doctor list in "
                                                           "staff file.")
        for ix, day in enumerate(self.days):
            if rawdata['Day'][ix] == 'Weekend':
                continue

            assert len(self.working[day]) == len(set(self.working[day])), f"Duplicate doctors found on {day}"
            assert len(self.offsite[day]) == len(set(self.offsite[day])), f"Duplicate doctors found on {day}"
            assert (self.staff.everyone ==
                    sorted(self.working[day] + self.offsite[day])), f"Missing doctors found on {day}"
            print(f"Day {day} passed sanity checks.")
        print("All days passed sanity checks.\n")

    @property
    def days(self):
        return self.rawdata['Order']

    @property
    def orders(self):
        highest_key = max(key for inner_dict in self.preassigned.values() for key in inner_dict.keys())
        return list(range(1, highest_key + 1))

    @property
    def Admin(self):
        return {day: self.rawdata['Admin'][d] for d, day in enumerate(self.days)}

    @property
    def charge_order(self):
        """
        Constructs and returns a dictionary representing the order in which charges are assigned for each day.
        For each day:
        - The base value is determined by the number of 'Whine' assignments.
        - An additional count is added based on the number of preassigned values that fall within a certain range
          (specifically, less than the number of 'Whine' assignments plus 2).
        """
        return {
            day: len(self.Whine[day]) + len([o for o in self.preassigned[day] if o < len(self.Whine[day]) + 2])
            for day in self.days}

    def transform_rawdata(self, rawdata, remove_placeholder=True):
        def get_offsite_doctors(day):
            """ Returns a list of doctors offsite on a given day. """
            d = rawdata['Order'].index(day)
            return [doctor for doctor in rawdata['Offsite'][d] if doctor != self.staff.unknown.ID]

        def get_working_doctors(day):
            """ Returns a list of doctors working on a given day. """
            d = rawdata['Order'].index(day)
            working = []
            for turn_order in self.TURN_ORDER:
                items = rawdata[turn_order][d]
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

        if remove_placeholder:
            for d, day in enumerate(rawdata['Order']):
                for turn_order in self.TURN_ORDER:
                    if rawdata[turn_order][d] is None:
                        continue
                    if ADMIN_IDENTIFIER in rawdata[turn_order][d]:
                        rawdata[turn_order][d].remove(ADMIN_IDENTIFIER)
                    if self.staff.unknown.ID in rawdata[turn_order][d]:
                        rawdata[turn_order][d].remove(self.staff.unknown.ID)

        working = {day: get_working_doctors(day) for day in rawdata['Order']}
        offsite = {day: get_offsite_doctors(day) for day in rawdata['Order']}

        assignments = {turn_order: {day: [] for day in rawdata['Order']} for turn_order in self.TURN_ORDER}
        for d, day in enumerate(rawdata['Order']):
            current_tally = 1
            for turn_order in self.TURN_ORDER:
                items = rawdata[turn_order][d]
                if isinstance(items, list):
                    if turn_order == 'Admin':
                        for item in items:
                            assignments[turn_order][day].append(Assignment(item, ADMIN_POINTS, turn_order))
                    else:
                        for item in items:
                            assignments[turn_order][day].append(
                                Assignment(item, range(current_tally, current_tally + len(items)),
                                           turn_order))
                        current_tally += len(items)
                elif items is not None:
                    assignments[turn_order][day].append(Assignment(items, current_tally, turn_order))
                    current_tally += 1

        return working, offsite, assignments

    def get_doctor_points_for_day(self, doctor, day, row=0):
        """Get the preassigned points for a doctor on a given day."""
        assert any([a for t in self.TURN_ORDER for a in self.assignments[t][day] if a.doctor == doctor]), \
            f"Doctor {doctor} not found on {day}."
        points = [a.points for t in self.TURN_ORDER for a in self.assignments[t][day] if a.doctor == doctor]
        assert len(points) == 1, f"Multiple points found for doctor {doctor} on {day}."
        points = points[0]
        return list(points)[row] if isinstance(points, range) else points

    def get_points_per_doctor(self, doctor, add_assigned=False):
        """Get the total points per doctor over the entire schedule."""
        tally = {day: 0 for day in self.days}
        for day in self.days:
            for t in self.TURN_ORDER:
                if t == 'Unassigned' and not add_assigned:
                    continue
                if t == 'Unassigned' and self.assigned:
                    tally[day] += sum([a.points for a in self.solution['Whine'][day] if a.doctor == doctor])
                elif t == 'Unassigned' and not self.assigned:
                    tally[day] += 0
                else:
                    tally[day] += sum([a.points for a in self.assignments[t][day] if a.doctor == doctor])

        return sum(tally.values())

    @property
    def assigned(self):
        """ If a placeholder doctor is found in the schedule, return False. """
        return all(assignment.doctor != self.staff.unknown.ID
                   for day, whine in self.solution['Whine'].items() for assignment in whine)

    def set_solution(self, solution):
        """ Set the solution to the given solution. """
        for day, assignments in solution['Whine'].items():
            for assignment in assignments:
                assert assignment.shift == 'Assigned', f'Invalid shift {assignment.shift} found in solution.'
                if assignment.doctor in self.preassigned[day].values():
                    continue
                else:
                    for i, whine in enumerate(self.solution['Whine'][day]):
                        if whine.points == assignment.points:
                            self.solution['Whine'][day][i] = assignment
                            break

        # Check that the solution matches the original unassigned pool of doctors
        for day in self.days:
            assert set(assignment.doctor for assignment in self.solution['Whine'][day]) == set(self.Whine[day]), \
                f"Whine zone on {day} does not match the solution."
            assert solution['Charge'][day] in self.working[day], f"Charge doctor not working on {day}"
            assert solution['Cardiac'][day] in self.working[day], f"Cardiac doctor not working on {day}"
            assert solution['Cardiac'][day] != solution['Charge'][day], f"Same doctor both charge and cardiac on {day}"

        self.solution['Charge'] = solution['Charge']
        self.solution['Cardiac'] = solution['Cardiac']
        self.solution['Points'] = solution['Points']
        self.solution['Target'] = solution['Target']
        self.solution['Objective'] = solution['Objective']

    def _print_schedule(self, color_cardiac=False, color_charge=False):
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

            max_rows = max(len(item) if item else 0 for item in values)
            if max_rows == 0:
                items = [key] + [''] * len(self.days) * 2
                output.append(row_format.format(*items))

            # Iterate for each row and print
            for row in range(max_rows):
                items = [key] + \
                        [apply_color(col[row].doctor) if row < len(col) and col[row] else '' for col in values] + \
                        [(list(col[row].points)[row] if isinstance(col[row].points, range) else col[row].points)
                         if row < len(col) and col[row] else '' for col in values]
                output.append(row_format.format(*items))

        # Define the row format.
        # The first placeholder reserves 10 spaces and the rest reserve 4 spaces each.
        row_format_short = "{:<12}" + "{:>4}" * len(self.days) + "  | "
        row_format = row_format_short + "{:>4}" * len(self.days)
        header = [""] + self.days + self.days
        header = row_format.format(*header)
        output.append(header)
        separator = '-' * len(header)

        for t, turn_order in enumerate(self.TURN_ORDER):
            if turn_order == "Unassigned":
                output.append(separator)
                if self.assigned:
                    print_nested_list('Assigned', self.solution['Whine'].values())
                else:
                    print_nested_list(turn_order, self.assignments[turn_order].values())
            elif turn_order == "Admin":
                output.append(separator)
                print_nested_list(turn_order, self.assignments[turn_order].values())
            else:
                print_nested_list(turn_order, self.assignments[turn_order].values())

        output.append(separator)
        # Print the charge doctors
        charge = [apply_color(item) for item in self.solution['Charge'].values()]
        row = ['Charge'] + charge
        output.append(row_format_short.format(*row))

        # Print the cardiac doctors
        cardiac = [apply_color(item) for item in self.solution['Cardiac'].values()]
        row = ['Cardiac'] + cardiac
        output.append(row_format_short.format(*row))

        # Print other daily statistics
        output.append(separator)

        # Print the total number of doctors working per day
        working = [len(self.working[day]) for day in self.days]
        sums = [sum([a.points if isinstance(a.points, int) else list(a.points)[i] for t in self.TURN_ORDER
                     for i, a in enumerate(self.assignments[t][day])]) for day in self.days]
        row = ['Working'] + working + sums
        output.append(row_format.format(*row))

        # Print the total number of doctors offsite per day
        offsite = [len(self.offsite[day]) for day in self.days]
        row = ['Offsite'] + offsite
        output.append(row_format_short.format(*row))

        # Print the total number of doctors per day
        total = [working[i] + offsite[i] for i in range(len(working))]
        row = ['Total'] + total
        output.append(row_format_short.format(*row))

        return "\n".join(output)

    def _print_doctors(self):
        """ Print information per doctor. """
        preassigned_points = {doc: self.get_points_per_doctor(doc, add_assigned=False) for doc in self.doctors}
        points_per_doctor = {doc: self.get_points_per_doctor(doc, add_assigned=True) for doc in self.doctors}

        charge = {doc: sum([1 for c in self.solution['Charge'].values() if c == doc]) for doc in self.doctors}
        cardiac = {doc: sum([1 for c in self.solution['Cardiac'].values() if c == doc]) for doc in self.doctors}

        row_format = "{:>10}{:>6}" + "{:>6}" * 5
        header = ["Name", "ID", "Pt0", "Pt", "Delta", CHARGE_IDENTIFIER, CARDIAC_IDENTIFIER]
        header = row_format.format(*header)
        separator = '-' * len(header)
        output = [header, separator]

        for doc in self.doctors:
            row = [self.staff.get_name(doc), doc,
                   preassigned_points[doc] if preassigned_points[doc] > 0 else '',
                   points_per_doctor[doc] if points_per_doctor[doc] > 0 else '',
                   points_per_doctor[doc] - self.solution['Target'] if points_per_doctor[doc] > 0
                                                                       and self.solution['Target'] is not None else '',
                   charge[doc] if charge[doc] > 0 else '',
                   cardiac[doc] if cardiac[doc] > 0 else ''
                   ]
            output.append(row_format.format(*row))
        output.append(separator)

        pre_points = pd.Series([preassigned_points[doc] for doc in self.doctors if preassigned_points[doc] > 0])
        post_points = pd.Series([points_per_doctor[doc] for doc in self.doctors if points_per_doctor[doc] > 0])
        offset = (post_points - self.solution['Target']) if self.solution['Target'] is not None else pd.Series([])

        # Calc and post points should match, but just in case...
        for doc in self.doctors:
            if doc in self.solution['Points'] and self.solution['Points'][doc] is not None:
                assert self.solution['Points'][doc] == points_per_doctor[doc], \
                    f'Calc points for {doc} does not match post points.'

        charge = pd.Series([charge[doc] for doc in self.doctors])
        cardiac = pd.Series([cardiac[doc] for doc in self.doctors])

        row = ['Average', '', round(pre_points.mean(), 1), round(post_points.mean(), 1), round(offset.mean(), 1),
               round(charge.mean(), 1), round(cardiac.mean(), 1)]
        output.append(row_format.format(*row))
        row = ['Median', '', round(pre_points.median(), 1), round(post_points.median(), 1), round(offset.median(), 1),
               round(charge.median(), 1), round(cardiac.median(), 1)]
        output.append(row_format.format(*row))
        row = ['Min', '', round(pre_points.min(), 1), round(post_points.min(), 1), round(offset.min(), 1),
               round(charge.min(), 1), round(cardiac.min(), 1)]
        output.append(row_format.format(*row))
        row = ['Max', '', round(pre_points.max(), 1), round(post_points.max(), 1), round(offset.max(), 1),
               round(charge.max(), 1), round(cardiac.max(), 1)]
        output.append(row_format.format(*row))
        output.append(separator)

        if self.solution['Target'] is not None:
            row_format = "{:>10}{:>7}{:>7}"
            output.append(row_format.format('Delta', 'Count', 'AbsSum'))
            for i in range(3):
                in_band = (offset.abs() == i)
                output.append(row_format.format(f"{i}:", in_band.sum(), offset[in_band].abs().sum()))
            in_band = (offset.abs() > i)
            output.append(row_format.format(f"{i + 1}+:", in_band.sum(), offset[in_band].abs().sum()))
            output.append(separator)
            row_format = "{:>15}{:>7}"
            output.append(row_format.format('Objective', 'Value'))
            for obj_var, obj_val in self.solution['Objective'].items():
                output.append(row_format.format(obj_var, obj_val))
            output.append(separator)
            output.append(f'Target: {self.solution["Target"]} points per doctor.')

        output.append(f'Count: {len(self.doctors)} doctors.')

        return "\n".join(output)

    def print(self, filename=None):
        """ Write the schedule and doctor information. If filename is None, print to stdout."""
        if filename is None:
            print(self._print_schedule(color_cardiac=True, color_charge=True))
            print('\n')
            print(self._print_doctors())
        else:
            with open(filename, 'w') as f:
                f.write(self._print_schedule())
                f.write('\n\n')
                f.write(self._print_doctors())


def main():
    parser = argparse.ArgumentParser(
        description="Load doctor's schedule from a file and optionally save output to another file.")
    parser.add_argument('input_filename', type=str, help='Path to the schedule input file.')
    parser.add_argument('--output', '-o', type=str, default=None, dest='output_filename',
                        help='Path to save the schedule output. Optional.')

    args = parser.parse_args()
    schedule = DoctorSchedule(args.input_filename)

    schedule.print()  # Print to stdout

    if args.output_filename is not None:
        schedule.print(args.output_filename)


if __name__ == "__main__":
    main()
