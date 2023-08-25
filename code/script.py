import configparser
import csv
import json
import os.path
from collections import defaultdict

import gurobipy as gp
from gurobipy import GRB

config = configparser.ConfigParser()
config.read('config.ini')

HARD = 'HARD'
SOFT = 'SOFT'
TBD = 'TBD'
CHARGE = 'CHARGE'
CARDIAC = 'CARDIAC'
ADMIN_POINTS = 8


class Anesthetist:
    def __init__(self, name, charge, cardiac):
        assert name is not None and name != ''
        assert type(charge) == bool
        assert type(cardiac) == bool
        self.name = name
        self.charge = charge
        self.cardiac = cardiac
        self.assg0 = 0
        self.pnts0 = 0

    def __eq__(self, other):
        if isinstance(other, Anesthetist):
            return self.name == other.name
        return False

    def __hash__(self):
        return hash(self.name)

    def __repr__(self):
        return f"{self.name} {'charge' if self.charge else ''} {'cardiac' if self.cardiac else ''} #{self.assg0}/{self.pnts0}"


class ScheduledAnesthetist(Anesthetist):
    def __init__(self, anesthetist, role, constraints, points=None, additional_role=None):
        assert type(anesthetist) == Anesthetist
        super().__init__(anesthetist.name, anesthetist.charge, anesthetist.cardiac)  # Call to parent constructor
        assert role is not None
        assert constraints in (HARD, SOFT)
        self.role = role
        self.points = points
        self.constraints = constraints
        self.additional_role = additional_role

    def __repr__(self):
        return f"{self.name} #{self.points}"


class Schedule:
    def __init__(self, filename='../data/Week0.json'):

        self.Wday = ['MON', 'TUE', 'WED', 'THU', 'FRI']
        """A dictionary of days to schedule"""

        self.unassigned_per_day = {}
        """A list of unassigned doctors per day, (e.g., {'MON': ['Joe','Jane'], 'TUE': [Jane]})."""

        self.transition_shift_roles = {}
        """A dictionary of transition shift roles, per role and per day"""

        self.requested = {}
        """A dictionary of requested roles, per role and per day"""

        self.shift_roles = {}
        """A dictionary of transition shift roles, per role and per day"""

        self.anst = {}
        """A dictionary of doctors, with their roles"""

        # Read a and set the doctors
        self.read_doctors()

        self.schedule_name = os.path.splitext(os.path.basename(filename))[0]
        """Name of the schedule"""

        # Read the schedule from the input file
        self.read_schedule(filename)

        # Update the points in self.anst based on the pre-allocated roles in the schedule
        self.update_points_based_on_roles()

    def read_schedule(self, filename_in):
        with open(filename_in, 'r') as file:
            data = json.load(file)

        # For 'unassignedPerDay'
        self.unassigned_per_day = data['unassignedPerDay']
        assert list(self.unassigned_per_day.keys()) == self.Wday

        points = defaultdict(int, {day: 1 for day in self.Wday})
        peeled = defaultdict(int, {day: 1 for day in self.Wday})

        # For 'transition-shift-roles'
        for entry in data["transition-shift-roles"]:
            role = entry.pop('role')
            self.transition_shift_roles[role] = {}
            for day, anst in entry.items():
                if anst:
                    self.transition_shift_roles[role][day] = ScheduledAnesthetist(self.anst[anst], role, SOFT,
                                                                                  points[day])
                    points[day] += 1

        # For 'requested'
        for entry in data['requested']:
            role = entry.pop('role')
            is_admin = role.startswith('Admin')

            self.requested[role] = {}
            unknown = Anesthetist(TBD, False, False)
            for day, anst in entry.items():
                if anst or peeled[day] < len(self.unassigned_per_day[day]):
                    person_value = self.anst[anst] if anst else unknown
                    person_points = ADMIN_POINTS if is_admin else points[day]
                    self.requested[role][day] = ScheduledAnesthetist(person_value, role, SOFT, person_points)

                    if not is_admin:
                        points[day] += 1

                        if not anst and peeled[day] < len(self.unassigned_per_day[day]):
                            peeled[day] += 1

        # For 'shift-roles'
        for day in self.Wday: points[day] += 1  # TODO remove ?
        for entry in data["shift-roles"]:
            role = entry.pop('role')
            self.shift_roles[role] = {}
            for day, anst in entry.items():
                if anst:
                    self.shift_roles[role][day] = ScheduledAnesthetist(self.anst[anst], role, HARD, points[day])
                    points[day] += 1

    def read_doctors(self, csv_file='../data/staff.csv'):
        with open(csv_file, mode='r') as file:
            # Create a csv reader object from the file
            reader = csv.DictReader(file)

            # Iterate over each row in the csv
            for row in reader:
                name = row['anst']
                cardiac = True if row['diac'] == 'TRUE' else False
                charge = True if row['chrg'] == 'TRUE' else False

                # Create an Anesthetist object
                self.anst[name] = Anesthetist(name, charge, cardiac)

    def update_points_based_on_roles(self):
        # Combine both dictionaries for simplicity
        all_roles = {**self.transition_shift_roles, **self.shift_roles}
        for role, assignments in all_roles.items():
            for day, person in assignments.items():
                # Ensure value is not "TBD" or empty
                if person and person.name != TBD:
                    if role in self.transition_shift_roles:
                        self.anst[person.name].assg0 += 1
                    self.anst[person.name].pnts0 += person.points

    def print(self, output_file=None):
        def custom_print(s=""):
            if output_file:
                file.write(s + "\n")
            else:
                print(s)

        def format_person(person):
            if person.additional_role == CARDIAC:
                name = f"\033[91m{person.name}\033[0m"  # Red
            elif person.additional_role == CHARGE:
                name = f"\033[94m{person.name}\033[0m"  # Blue
            else:
                name = person.name
            return f"{name} ({person.points})"

        def print_table(data_dict):
            header = "{:<15}" + "{:<12}" * 5
            row_format = "{:<15}" + "{:<12}" * 5

            # Print header
            custom_print(header.format("Role", *self.Wday))
            custom_print('-' * 75)  # Print a separator line

            # Print each role's assignments
            for role, assignments in data_dict.items():
                row_data = []
                for day in self.Wday:
                    if day in assignments:
                        person_data = assignments[day]
                        row_data.append(f"{format_person(person_data)}")
                    else:
                        row_data.append('')
                custom_print(row_format.format(role, *row_data))

        def print_doctors():
            cols = ['Chrg', 'Diac', 'Pnts0', 'Assg0']
            header = "{:<5}" + "{:<6}" * len(cols)
            row_format = "{:<5}" + "{:<6}" * len(cols)

            # Print header
            custom_print(header.format("Name", *cols))
            custom_print('-' * 75)  # Print a separator line

            for name, anst in self.anst.items():
                row_data = [
                    '*' if anst.charge else '',
                    '*' if anst.cardiac else '',
                    anst.pnts0,
                    anst.assg0
                ]
                custom_print(row_format.format(name, *row_data))

        if output_file:
            file = open(output_file, 'w')
        try:
            custom_print(self.schedule_name)  # Print a separator line
            custom_print('=' * 75)  # Print a separator line
            custom_print("\nTransition Shift Roles:")
            print_table(self.transition_shift_roles)
            custom_print("\nRequested:")
            print_table(self.requested)
            custom_print("\nShift Roles:")
            print_table(self.shift_roles)

            custom_print("\n\nDoctors:")
            print_doctors()
        finally:
            if output_file:
                file.close()


class Gurobi:
    def __init__(self, schedule):
        # Initialize model
        self.m = gp.Model("Anesthesiologist peel assignment problem (APAP)")
        """ Gurobi model """

        self.Wday = [day for day in schedule.Wday]
        """ List of days """

        self.Whine = schedule.unassigned_per_day
        """Dictionary of unassigned doctors for the day, e.g. {'MON': ['CA', 'CC'], 'TUE': ['BK']}"""

        self.Peel = list(range(4, 15))  # TODO - remove ?

        self.Anst = sorted([name for name in schedule.anst])
        """List of all doctors """

        self.Diac = sorted([name for name, anst in schedule.anst.items() if anst.cardiac])
        """List of all cardiac doctors """

        self.Chrg = sorted([name for name, anst in schedule.anst.items() if anst.charge])
        """List of all doctors that can be in charge """

        self.onCall = {day: anst.name for day, anst in schedule.shift_roles['Call'].items()}
        """Dictionary with the on call doctor, e.g. {'MON': 'TT', 'TUE': 'AY', 'WED': 'KC', 'THU': 'ES', 'FRI': 'SL'}"""

        self.onLate = {day: anst.name for day, anst in schedule.shift_roles['Late'].items()}
        """Dictionary with the on late doctor, e.g. {'MON': 'RR', 'TUE': 'SL', 'WED': 'CA', 'THU': 'JJ', 'FRI': 'RR'}"""

        self.Pnts0 = {name: anst.pnts0 for name, anst in schedule.anst.items()}
        """Dictionary with the total preallocated points per doctor, e.g. {'AY': 20, 'BK': 2}"""

        self.Assg0 = {name: anst.assg0 for name, anst in schedule.anst.items()}
        """Dictionary with total number of transitional shifts per doctor, e.g. {'AY': 3, 'BK': 1}"""

        self.Prep0 = {}  # TODO

        self.mCardio = {
            day: not schedule.shift_roles['Call'][day].cardiac and not schedule.shift_roles['Late'][day].cardiac
            for day in self.Wday}
        """Dictonary per day if there is a cardio doctor missing in the shift-role """

        self.mCharge = {
            day: not schedule.shift_roles['Call'][day].charge and not schedule.shift_roles['Late'][day].charge
            for day in self.Wday}
        """Dictonary per day if there is a charge doctor missing in the shift-role """

        self.SpPeel = {}  # TODO
        """Dictionary with special peel positions for each anesthetist, day, and position."""

        # Filtered sets for compactness
        self.AWP = [(a, d, p) for d in self.Wday for a in self.Whine[d] for p in self.Peel[:(1 + len(self.Whine[d]))]]
        """ AWP all possible assignments, e.g. [('CA', 'MON', 4), ('CA', 'MON', 5), ('TT', 'FRI', 11)] """

        self.AdW = [(a, d) for d in self.Wday for a in self.Whine[d] + [self.onCall[d]] + [self.onLate[d]]
                    if a in self.Diac]
        """ AdW all possible cardio assignments, [('CA', 'MON'), ('CC', 'MON'), ('RR', 'FRI')]"""
        self.AcW = [(a, d) for d in self.Wday for a in self.Whine[d] + [self.onCall[d]] + [self.onLate[d]]
                    if a in self.Chrg]
        """ AcW all possible charge assignments, [('BK', 'MON'), ('CC', 'MON'), ('JJ', 'FRI')]"""

        self.x = self.m.addVars(self.AWP, vtype="B")
        """ Assigned position """

        # Compute sum of points
        self.y = self.m.addVars(self.Anst, vtype="C")
        # Maximum points per any individual
        self.z1 = self.m.addVar()
        self.z2 = self.m.addVar()
        self.z3 = self.m.addVar()
        self.z4 = self.m.addVar()

        self.h = self.m.addVars(self.AdW, vtype="B")
        """ h is who Cardio of the day """

        self.c = self.m.addVars(self.AcW, vtype="B")
        """ c is the Charge of the day """

        self.zcha = self.m.addVar()  # max combined per a in Anst
        self.zch = self.m.addVars(self.Anst)

    def set_hard_constraints(self):
        # Those that have not been assigned to a slot yet must be assigned:
        self.m.addConstrs(
            gp.quicksum(
                self.x[a, d, p] for p in self.Peel[:(1 + len(self.Whine[d]))]
            ) == 1 for d in self.Wday for a in self.Whine[d])

        # Can only assign one per peel per wday
        self.m.addConstrs(
            gp.quicksum(
                self.x[a, d, p] for a in self.Whine[d]
            ) <= 1 for d in self.Wday for p in self.Peel[:(1 + len(self.Whine[d]))]
        )

        # The approximate amount of points assigned to each Anesthetist
        if False:  # TODO
            self.m.addConstrs(
                gp.quicksum(self.x[a, d, p] * (p + self.Prep0[d])
                            for d in self.Wday for p in self.Peel
                            if (a, d, p) in self.AWP) + self.Pnts0[a] == self.y[a] for a in self.Anst
            )

        # now for the special conditions:
        # If we have a Cardio or Charge missing from any given day, then we should force them to be late out
        self.m.addConstrs(
            gp.quicksum(
                self.x[a, d, p] for a in self.Diac for p in self.Peel[(len(self.Whine[d]) - 1):(1 + len(self.Whine[d]))]
                if (a, d) in self.AdW
            ) >= 1 for d in self.Wday if self.mCardio[d]
        )

        self.m.addConstrs(
            gp.quicksum(
                self.x[a, d, p] for a in self.Chrg for p in self.Peel[(len(self.Whine[d]) - 1):(1 + len(self.Whine[d]))]
                if (a, d) in self.AcW
            ) >= 1 for d in self.Wday if self.mCharge[d]
        )

        # Tricky condition, minimizing the number of Cardio and Charge over the week, it works!
        self.m.addConstrs(
            gp.quicksum(
                self.c[a, d] for a in self.Whine[d] + [self.onCall[d]] + [self.onLate[d]] if a in self.Chrg
            ) == 1 for d in self.Wday
        )
        self.m.addConstrs(
            gp.quicksum(
                self.h[a, d] for a in self.Whine[d] + [self.onCall[d]] + [self.onLate[d]] if a in self.Diac
            ) == 1 for d in self.Wday
        )

        # The same person cannot take both roles:
        self.m.addConstrs(
            gp.quicksum(
                self.h[a, d] + self.c[a, d] for a in self.Chrg if (a, d) in self.AdW and (a, d) in self.AcW
            ) <= 1 for d in self.Wday
        )
        # Now if we have decided the role then they must either be late or on call
        self.m.addConstrs(
            gp.quicksum(
                self.x[a, d, p] for p in self.Peel[(len(self.Whine[d]) - 1):(1 + len(self.Whine[d]))]
            ) >= self.h[a, d] for (a, d) in self.AdW if (a != self.onCall[d]) and (a != self.onLate[d])
        )
        self.m.addConstrs(
            gp.quicksum(
                self.x[a, d, p] for p in self.Peel[(len(self.Whine[d]) - 1):(1 + len(self.Whine[d]))]
            ) >= self.c[a, d] for (a, d) in self.AcW if (a != self.onCall[d]) and (a != self.onLate[d])
        )
        # now calculate the maximum number on Cardio or Charge
        self.m.addConstrs(
            gp.quicksum(
                self.h[a, d] for d in self.Wday if (a, d) in self.AdW
            ) +
            gp.quicksum(
                self.c[a, d] for d in self.Wday if (a, d) in self.AcW
            ) <= self.zch[a] for a in self.Chrg if a in self.Diac
        )

        self.m.addConstrs(
            gp.quicksum(self.c[a, d] for d in self.Wday if (a, d) in self.AcW) <= self.zch[a] for a in self.Chrg
        )
        self.m.addConstrs(
            gp.quicksum(self.h[a, d] for d in self.Wday if (a, d) in self.AdW) <= self.zch[a] for a in self.Diac
        )
        self.m.addConstrs(self.zch[a] <= self.zcha for a in self.Diac)

        # Only once in the end peel
        self.m.addConstrs(
            gp.quicksum(
                self.x[a, d, p] for d in self.Wday for p in self.Peel[len(self.Whine[d]) - 1:len(self.Whine[d])]
                if (a, d, p) in self.AWP
            ) <= 1 for a in self.Anst)

        # Special requests, fixed for Whine[d]
        self.m.addConstrs(
            self.x[a, d, p] == 1 for (a, d, p) in self.SpPeel.keys() if (a, d, p) in self.AWP
        )

    def set_soft_constraints(self):
        # The maximum number (two layered press!)
        self.m.addConstrs(self.y[a] <= self.z1 for a in self.Anst if self.Assg0[a] < 4)
        self.m.addConstrs(self.y[a] <= self.z2 for a in self.Anst)
        self.m.addConstrs(self.y[a] >= self.z3 for a in self.Anst if self.Assg0[a] < 4)
        self.m.addConstrs(self.y[a] >= self.z4 for a in self.Anst)

    def set_objective_function(self):
        # minimize the maximum (worst case)
        self.m.setObjective(
            gp.quicksum(self.y[a] for a in self.Anst) +
            gp.quicksum(self.zch[a] for a in self.Anst) + 10000 * self.z1 +
            10000 * self.z2 - 1 * self.z3 - 1 * self.z4 + 100 * self.zcha
            , GRB.MINIMIZE
        )
        # self.m.setObjective(gp.quicksum(y[a] for a in Anst) + 1000*z2 + gp.quicksum(zch[a] for a in Anst), GRB.MINIMIZE)

    def solve(self):
        """ Optimize model and print solution"""
        self.m.optimize()

        header = "{:<15}" + "{:<12}" * 5
        row_format = "{:<15}" + "{:<12}" * 5
        print(header.format("Peel", *self.Wday))
        print('-' * 75)  # Print a separator line

        sol = {}
        for p in self.Peel:
            row_data = []
            for d in self.Wday:
                value_assigned = False
                for a in self.Anst:  # Assuming A is the set/list for 'a' values
                    if (a, d, p) in self.x and self.x[a, d, p].X > 0.5:
                        name = a
                        if (a, d) in self.h and int(self.h[a, d].X) > 0:
                            name += '\u2665'  # add a little heart ♥ for cardiac
                        if (a, d) in self.c and int(self.c[a, d].X) > 0:
                            name += '\u2699'  # add a little gear ⚙ for charge

                        row_data.append(name)
                        value_assigned = True
                        break  # if one 'a' satisfies the condition, we break,
                        # because only one 'a' can be > 0.5 for a given [d,p]

                if not value_assigned:
                    row_data.append('')
            sol[p] = {d: a for (a, d, p) in self.AWP if self.x[a, d, p].X > 0.5}
            print(row_format.format(p, *row_data))

        charge = {day: [] for day in self.Wday}
        for (a, d) in self.AcW:
            if int(self.c[a, d].X) > 0:
                charge[d].append(a)
        row_data = [",".join(charge[d]) for d in self.Wday]
        print(row_format.format('charge', *row_data))

        cardio = {day: [] for day in self.Wday}
        for (a, d) in self.AdW:
            if int(self.h[a, d].X) > 0:
                cardio[d].append(a)
        row_data = [",".join(cardio[d]) for d in self.Wday]
        print(row_format.format('cardio', *row_data))

        # display the points per person:
        print("Points per person:")
        ppp = {}
        for a in self.Anst:
            if int(self.y[a].X) > 0:
                print(int(self.y[a].X) + 0 * self.Pnts0[a], ":", a)
                ppp[a] = int(self.y[a].X + 0 * self.Pnts0[a])

        print("max number of cardio+charge=", self.zcha.X)

        return sol, ppp


def main():
    schedule = Schedule('../data/Week0.json')
    schedule.print('../data/Week0.init.txt')
    opt = Gurobi(schedule)
    opt.set_hard_constraints()
    # opt.set_soft_constraints()
    opt.set_objective_function()
    sol, ppp = opt.solve()

main()
