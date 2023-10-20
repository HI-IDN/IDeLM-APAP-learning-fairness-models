from gurobipy import Model, GRB
from data.utils import read_and_remove_file, extract_values_from_text, write_json
from data.schedule import ADMIN_POINTS, Assignment


class AllocationModel:

    def __init__(self, data, simple=False):
        # Initialize the model
        self.m = Model("DoctorScheduling")
        self.data = data  # DataHandler object, known parameters

        # Derived variables
        self.solution = None  # Dictionary containing the solution to the model

        # Set up the model
        self._set_decision_variables()
        self._calculate_total_order()  # create a dict containing the total order for each doctor
        self._set_constraints()
        if not simple:
            self._set_additional_constraints()
        self._set_objective()

    def solve(self):
        """Optimize the model."""
        self.m.optimize()

        if self.m.status == GRB.OPTIMAL:
            self.solution = self._get_solution()
            self.data.set_solution(self.solution)
            return True
        else:
            return False

    def _get_solution(self):
        """Get the solution to the model."""
        whine = {}
        for day in self.data.weekdays:
            whine[day] = []
            for order in self.data.orders:
                for doctor in self.data.doctors:
                    if self.x[doctor, day, order].X > 0.5:  # If this doctor is assigned to this order on this day
                        whine[day].append(Assignment(doctor, order, 'Assigned'))
                        break  # Move to the next order once a doctor is found

        chrg = {day: [doctor] for day in self.data.weekdays for doctor in self.data.doctors
                if doctor in self.data.staff.charge_doctors and self.z[doctor, day].X == 1}
        diac = {day: [doctor] for day in self.data.weekdays for doctor in self.data.doctors
                if doctor in self.data.staff.cardiac_doctors and self.w[doctor, day].X == 1}

        # Sanity checks
        for day in self.data.weekdays:
            assert len(chrg[day]) == 1, f"Only one doctor can be assigned to charge on {day}: {chrg[day]}"
            assert len(diac[day]) == 1, f"Only one doctor can be assigned to cardiac on {day}: {diac[day]}"
            chrg[day] = chrg[day][0]
            diac[day] = diac[day][0]

        points = {doctor: int(total_order.getValue()) for doctor, total_order in self.total_order.items()}
        target = int(self.central_value.X)

        # Objective values
        obj = {
            'equity': self.obj_var['equity'].X,
            'cardiac_charge': self.obj_var['cardiac_charge'].X,
            'priority_charge': self.obj_var['priority_charge'].X,
            'total': self.obj_var['total'].X
        }
        return {'Whine': whine, 'Charge': chrg, 'Cardiac': diac, 'Points': points, 'Target': target, 'Objective': obj}

    def _set_decision_variables(self):
        """Create decision variables for the model."""

        # Binary variables to indicate if a doctor is assigned to a particular order on a particular day
        self.x = self.m.addVars(self.data.doctors, self.data.days, self.data.orders, vtype=GRB.BINARY,
                                name="DoctorOrderAssignment_x")
        """
        x[doctor, day, order]: 
        1 if the doctor is assigned to a particular order on the specified day; 0 otherwise.
        """

        # Variable representing the target total_order value for all doctors
        self.central_value = self.m.addVar(vtype=GRB.INTEGER, name="TargetTotalOrderValue_central_value")
        """
        central_value:
        Represents the target value for total orders across all doctors.
        """

        # Binary variables to capture specific doctor conditions
        self.y = self.m.addVars(self.data.doctors, vtype=GRB.BINARY, name="DoctorCondition_y")
        """
        y[doctor]: 
        1 if specific conditions (defined elsewhere in the code) are met for the doctor; 0 otherwise.
        """

        # Binary variables to indicate if a doctor is in charge for a particular day
        self.z = self.m.addVars(self.data.staff.charge_doctors, self.data.weekdays, vtype=GRB.BINARY,
                                name="InChargeDoctor_z")
        """
        z[doctor, day]: 
        1 if the doctor is in charge on the specified day; 0 otherwise.
        """

        # Binary variables to indicate if a doctor is the Cardiac doctor for the day
        self.w = self.m.addVars(self.data.staff.cardiac_doctors, self.data.weekdays, vtype=GRB.BINARY,
                                name="CardiacDoctor_w")
        """
        w[doctor, day]: 
        1 if the doctor is assigned as the Cardiac doctor on the specified day; 0 otherwise.
        """

        # Variable representing the maximum number of times any doctor is assigned the "Cardiac" role
        self.max_w = self.m.addVar(name="MaxAssignmentsAsCardiac_max_w")
        """
        max_w:
        Represents the maximum number of times any doctor is assigned the "Cardiac" role.
        """

        # Variable representing the maximum number of times any doctor is in charge
        self.max_z = self.m.addVar(name="MaxAssignmentsInCharge_max_z")
        """
        max_z:
        Represents the maximum number of times any doctor is designated as "in charge".
        """

        # Variable to determine the maximum times a doctor holds both "Cardiac" and "Charge" roles over the week
        self.max_wz = self.m.addVar(name="MaxAssignmentsBothRoles_max_wz")
        """
        max_wz:
        Indicates the maximum times any doctor holds both the "Cardiac" and "Charge" roles over a week.
        """

    def _set_constraints(self):
        """Create all mandatory constraints."""

        # Ensure each order on a day is assigned to at most one doctor.
        self._add_order_uniqueness_constraint()

        # Ensure unscheduled doctors are not assigned any orders.
        self._set_values_zero_for_unscheduled_doctors()

        # Ensure no doctor is assigned an order beyond the last preassigned one.
        self._restrict_orders_beyond_last_call()

        # Assign constraints for doctors who have predetermined orders on specific days.
        self._add_preassigned_doctor_constraints()

        # Distribute orders among doctors in an equitable manner.
        self._add_constraints_for_doctor_order_equity()

    def _set_additional_constraints(self):
        """Create additional constraints."""

        # Assign constraints for doctors from the 'Whine' group for each day.
        self._add_whine_doctor_constraints()

        # Add constraints for the "Cardiac" role.
        total_in_cardiac = self._add_cardiac_constraints()
        # Add constraints for the "Charge" role.
        total_in_charge = self._add_charge_constraints()

        # Ensure no doctor can serve both as a "Cardiac" and a "Charge" doctor on the same day.
        self._add_no_cardiac_and_charge_dual_role_constraints(total_in_cardiac, total_in_charge)

        # Ensure no doctor is assigned the "Charge" role for two consecutive days.
        self._add_no_consecutive_charge_constraints()

    def _set_objective(self):
        """
        Set the optimization objective for the model.

        The objective aims to:
        1. Maximize equity among doctors in terms of work distribution.
        2. Minimize the maximum number of times any doctor is assigned the "Cardiac" or "In Charge" roles.
        3. Prioritize doctors in 'call_and_late_call_doctors' list to be "In Charge".

        The objectives are combined using weighted coefficients:
        - `alpha` for equity (most important).
        - `beta` for minimizing "Cardiac" and "In Charge" roles.
        - `gamma` for increasing the likelihood of doctors from 'call_and_late_call_doctors' to be "In Charge" on
        specific days.

        """
        # Weights for different objectives
        alpha = 1  # Weight for the equity objective
        beta = 0.1  # Weight for the "In Charge" and "Cardiac" objectives
        gamma = 0.001  # Weight to prioritize certain doctors for "In Charge" role on specific days

        # Define individual objectives
        self.obj_var = {
            'equity': self.m.addVar(name="equity_obj"),
            'cardiac_charge': self.m.addVar(name="cardiac_charge_obj"),
            'priority_charge': self.m.addVar(name="priority_charge_obj"),
            'total': self.m.addVar(name="total_obj")  # Dummy variable to combine the objectives
        }

        # Linking the equity objective to the dummy variable
        self.m.addConstr(self.obj_var['equity'] == sum(self.y[doctor] for doctor in self.data.doctors))

        # Linking the cardiac charge objective to the dummy variable
        self.m.addConstr(self.obj_var['cardiac_charge'] == self.max_w + self.max_z + self.max_wz)

        # Linking the priority charge objective to the dummy variable
        self.m.addConstr(
            self.obj_var['priority_charge'] == sum(
                self.z[doctor, day] for day in self.data.weekdays
                for doctor in self.data.staff.charge_doctors
                if doctor in self.data.call_doctors[day]
            )
        )

        # Combine the objectives using the weights
        self.m.addConstr(self.obj_var['total'] ==
                         + alpha * self.obj_var['equity']
                         - beta * self.obj_var['cardiac_charge']
                         + gamma * self.obj_var['priority_charge']
                         )

        # Set the objective to maximize
        self.m.setObjective(self.obj_var['total'], GRB.MAXIMIZE)

    def _add_order_uniqueness_constraint(self):
        """
        Ensure that each order on a given day is assigned to at most one doctor.
        """
        self.m.addConstrs(
            (sum(self.x[doctor, day, order] for doctor in self.data.doctors) <= 1
             for day in self.data.days for order in self.data.orders),
            name="unique_order_assignment"
        )

    def _add_whine_doctor_constraints(self):
        """
        Ensure that each doctor in Whine[day] is assigned exactly one order per day.
        """
        # Each doctor in Whine[day] is assigned to one order per day
        self.m.addConstrs(
            (sum(self.x[doctor, day, order] for order in self.data.orders) == 1
             for day in self.data.weekdays for doctor in self.data.Whine[day]),
            name="whine_doctor_order_assignment"
        )

    def _add_preassigned_doctor_constraints(self):
        """
        Set constraints for doctors that are preassigned to specific orders and days.
        """
        # Ensure pre-assigned doctors are only at one place
        self.m.addConstrs(
            (sum(self.x[doctor, day, order] for order in self.data.orders) == 1
             for day in self.data.days for doctor in list(self.data.preassigned[day].values())),
            name="preassigned_doctor_order_assignment"
        )

        # Pre-assigned doctors
        for day, order_doctor_dict in self.data.preassigned.items():
            for order, doctor in order_doctor_dict.items():
                self.m.addConstr(self.x[doctor, day, order] == 1)

    def _set_values_zero_for_unscheduled_doctors(self):
        """
        For each day, set the assignment decision variables (x values) to zero for doctors
        who are not scheduled. This ensures that doctors who are not available for the day
        are not assigned any orders.
        """
        for day in self.data.weekdays:
            # Get the set of doctors who are scheduled for the day
            scheduled_doctors = set(self.data.Whine[day] + list(self.data.preassigned[day].values()))

            # Identify doctors who are not scheduled
            not_scheduled = [doctor for doctor in self.data.doctors if doctor not in scheduled_doctors]

            # Set x values to zero for these doctors
            self.m.addConstrs(self.x[doctor, day, order] == 0 for order in self.data.orders for doctor in not_scheduled)

    def _restrict_orders_beyond_last_call(self):
        """
        For each day, ensure that no doctor is assigned an order that surpasses the last
        preassigned order (interpreted as the "call" or the last doctor out). This helps
        maintain the order of assignments in accordance with the preassigned schedule.
        """
        for day in self.data.days:
            # Ensure no doctor is assigned an order beyond the last preassigned one
            self.m.addConstrs(
                self.x[doctor, day, order] == 0
                for doctor in self.data.doctors
                for order in self.data.orders
                if order > list(self.data.preassigned[day].keys())[-1]
            )

    def _add_constraints_for_doctor_order_equity(self):
        """
        Add constraints to ensure that the total order for each doctor remains
        around a central value, considering administrative duties.

        The central value represents a target order assignment for all doctors.
        The constraints use the "big-M" method to create a boundary around this
        central value. A binary variable `self.y[doctor]` will be set to 1 if a
        doctor's total order deviates from this central value by more than one unit.
        """
        # Large constant for big-M method; used for linearizing the constraints
        M = len(self.data.days) * len(self.data.orders)

        # Constraints to ensure the total order for each doctor is around the central_value.
        # If a doctor's total order is not within the range (central_value - 1, central_value + 1),
        # the corresponding self.y[doctor] variable will be set to 1.
        self.m.addConstrs(
            (self.total_order[doctor] - (self.central_value - 1) >= -M * (1 - self.y[doctor])
             for doctor in self.data.doctors),
            name="lower_bound_order_constraint"
        )
        self.m.addConstrs(
            ((self.central_value + 1) - self.total_order[doctor] >= -M * (1 - self.y[doctor])
             for doctor in self.data.doctors),
            name="upper_bound_order_constraint"
        )

    def _add_cardiac_constraints(self):
        """
        Add constraints related to the "Cardiac" role, aka the "w" variables.

        1. Ensure that only one doctor with the role "Cardiac" is assigned each day.
        2. Calculate the total number of times each doctor is assigned the "Cardiac" role over the week.
        3. Ensure that the total number of times each doctor is assigned the "Cardiac" role does not exceed the maximum allowed.

        Uses:
        - w[doctor, day] binary decision variables: Represents whether a doctor is assigned the "Cardiac" role on a given day.
        - max_w: Variable representing the maximum number of times any doctor is assigned the "Cardiac" role.

        Returns:
            dict: Dictionary containing total number of times each doctor is assigned the "Cardiac" role over the week.
        """
        # Ensure each day has exactly one Cardiac doctor
        self.m.addConstrs(
            (sum(self.w[doctor, day] for doctor in self.data.potential_cardiac_doctors[day]) == 1
             for day in self.data.weekdays), name="one_cardiac"
        )

        # Calculate total times each doctor is assigned the "Cardiac" role over the week
        total_in_cardiac = {
            doctor: sum(
                self.w[doctor, day] for day in self.data.weekdays if doctor in self.data.call_doctors[day])
            for doctor in self.data.staff.cardiac_doctors
        }

        # Ensure no doctor is assigned the "Cardiac" role more than the maximum allowed times
        self.m.addConstrs(
            total_in_cardiac[doctor] <= self.max_w for doctor in self.data.staff.cardiac_doctors
        )

        return total_in_cardiac

    def _add_charge_constraints(self):
        """
        Add constraints related to the "Charge" doctor role, aka the "z" variables.

        1. Ensure that only one doctor from potential charge doctors is in the "Charge" role each day.
        2. Ensure that if a doctor is in the "Charge" role, they must have the corresponding order for that day.
        3. Calculate the total times each doctor is in the "Charge" role over the week.
        4. Ensure that the total number of times each doctor is in the "Charge" role does not exceed the maximum allowed.

        Uses:
        - z[doctor, day] binary decision variables: Represents whether a doctor is the "Charge" doctor on a given day.
        - max_z: Variable representing the maximum number of times any doctor is in the "Charge" role.
        - x[doctor, day, order] binary decision variables: Represents whether a doctor is assigned a specific order on a day.

        Returns:
            dict: Dictionary containing total number of times each doctor is assigned the "Charge" role over the week.
        """
        # Ensure only one potential charge doctor is in charge each day
        self.m.addConstrs(
            (sum(self.z[doctor, day] for doctor in self.data.potential_charge_doctors[day]) == 1
             for day in self.data.weekdays), name="one_in_charge"
        )

        # Ensure that if a doctor is in charge, they have the corresponding order for the day
        self.m.addConstrs(
            (self.x[doc, day, self.data.charge_order[day]] >= self.z[doc, day]
             for day in self.data.weekdays for doc in self.data.staff.charge_doctors if doc in self.data.Whine[day]),
            name="charge_order_constr"
        )

        # Calculate total times each doctor is in charge over the week
        total_in_charge = {
            doctor: sum(self.z[doctor, day] for day in self.data.weekdays) for doctor in self.data.staff.charge_doctors
        }

        # Ensure no doctor is in charge more than the maximum allowed times
        self.m.addConstrs(
            total_in_charge[doctor] <= self.max_z for doctor in self.data.staff.charge_doctors
        )

        return total_in_charge

    def _add_no_cardiac_and_charge_dual_role_constraints(self, total_in_cardiac, total_in_charge):
        """
        Add constraints to ensure that a doctor cannot simultaneously assume the "Cardiac" and "Charge" roles on the same day.

        1. Identify doctors who can assume both the "Cardiac" and "Charge" roles.
        2. For these doctors, ensure they cannot be assigned both roles on the same day.
        3. Ensure that the total combined roles (both "Cardiac" and "Charge") each doctor assumes over the week does
           not exceed the maximum allowed.

        Parameters:
        - total_in_cardiac: Dictionary containing the total number of times each doctor is assigned the "Cardiac"
                            role over the week.
        - total_in_charge:  Dictionary containing the total number of times each doctor is assigned the "Charge"
                            role over the week.

        Uses:
        - w[doctor, day] binary decision variables: Represents whether a doctor is the "Cardiac" role on a given day.
        - z[doctor, day] binary decision variables: Represents whether a doctor is the "Charge" doctor on a given day.
        """

        # Identify doctors who can assume both the Cardiac and Charge roles
        common_doctors = set(self.data.staff.charge_doctors) & set(self.data.staff.cardiac_doctors)

        # Ensure that doctors in the common_doctors set cannot take on both roles simultaneously for each day
        self.m.addConstrs(
            (self.w[doctor, day] + self.z[doctor, day] <= 1 for doctor in common_doctors for day in self.data.weekdays),
            name="cardiac_charge_conflict"
        )

        # Ensure no doctor takes on combined roles more than the maximum allowed times
        self.m.addConstrs(
            (total_in_charge[doctor] + total_in_cardiac[doctor] <= self.max_wz for doctor in common_doctors),
            name="max_combined_roles")

    def _calculate_total_order(self):
        """
        Calculate the total order for each doctor based on their assignments across all days and orders.
        Adjust the total_order values based on administrative duties.

        Attributes:
            total_order (dict): Contains the total order count for each doctor.
            x (dict): A multi-key dictionary that represents the assignment of doctors to days and orders.
            data (object): An object that contains days, orders, and doctors information.
        """

        # Calculate the Total Order for Each Doctor based on their assignments over all days and orders
        total_order = {
            doctor: sum(order * self.x[doctor, day, order] for day in self.data.days for order in self.data.orders)
            for doctor in self.data.doctors
        }

        # Adjust the total_order values based on administrative duties
        self.total_order = self._adjust_total_order_for_admin_duties(total_order)

    def _adjust_total_order_for_admin_duties(self, total_order):
        """
        Adjust the total order for doctors who have administrative duties.

        Doctors with administrative duties receive an additional 'q' points to
        their total order for every day they have an administrative role.

        Parameters:
            total_order (dict): Dictionary containing the total order values for doctors.
        Returns:
            dict: Updated total_order values after accounting for administrative duties.
        """
        # Loop through each day's administrative doctors
        for admin_doctors in self.data.Admin.values():
            for doctor in admin_doctors:
                total_order[doctor] += ADMIN_POINTS

        return total_order

    def _add_no_consecutive_charge_constraints(self):
        """
        Add constraints to ensure that no doctor is assigned the "Charge" role
        for two consecutive days.

        Uses binary decision variables z[doctor, day] to represent whether a doctor
        is the "Charge" doctor on a given day. For each doctor and for each pair of
        consecutive days, a constraint is added to ensure that the doctor isn't
        assigned the "Charge" role on both of those days.
        """
        for doctor in self.data.staff.charge_doctors:
            for i in range(len(self.data.days) - 1):  # -1 because we're looking at pairs of days
                day1 = self.data.days[i]
                day2 = self.data.days[i + 1]
                if day1 in self.data.weekdays and day2 in self.data.weekdays:
                    self.m.addConstr(self.z[doctor, day1] + self.z[doctor, day2] <= 1,
                                     name=f"no_consecutive_charge_{doctor}_{day1}_{day2}")

    def print(self, filename=None):
        """ Print the solution to the model. """
        self.data.print(filename)

    def save(self, filename):
        """ Save the solution to the model. """
        data = self.data.rawdata
        data['Solution'] = {
            'Assignment': [[(a.doctor, a.points) for a in self.solution['Whine'][day]] if day in self.data.weekdays
                           else None for day in self.data.days],
            'Charge': [self.solution['Charge'][day] if day in self.data.weekdays else None for day in self.data.days],
            'Cardiac': [self.solution['Cardiac'][day] if day in self.data.weekdays else None for day in self.data.days],
            'Points': self.solution['Points'],
            'Target': self.solution['Target'],
        }
        write_json(data, filename, overwrite=True)

    def debug_constraints(self):
        """ Warn if any constraints will definitely be violated."""
        if self.m.status == GRB.OPTIMAL:
            return

        # For more detailed information about infeasibility
        self.m.computeIIS()  # Computes an Irreducible Inconsistent Subsystem of constraints
        temp_file = "data/temp_iis.ilp"
        self.m.write(temp_file)
        error_message = read_and_remove_file(temp_file)
        print(error_message)

        # Print staff for troublesome days
        days = extract_values_from_text(error_message, self.data.days)
        print("Staff for troublesome days:")
        for day in days:
            print(f"Day {day}:")
            print(f"Potential Charge Doctors: {self.data.potential_charge_doctors[day]}")
            print(f"Potential Cardiac Doctors: {self.data.potential_cardiac_doctors[day]}")
            print(f'Whine Doctors: {self.data.Whine[day]}')
            print(f'Admin Doctors: {self.data.Admin[day]}')
            print(f'Preassigned Doctors: {self.data.preassigned[day]}')

        for day in self.data.weekdays:
            if day not in self.data.potential_charge_doctors:
                raise ValueError(f"'potential_charge_doctors' does not have the day {day}")
            if day not in self.data.potential_cardiac_doctors:
                raise ValueError(f"'potential_cardiac_doctors' does not have the day {day}")

        # Check if the length of the list of doctors for each day is >= 1
        for day, doctors_list in self.data.potential_charge_doctors.items():
            if day in self.data.weekdays and len(doctors_list) < 1:
                raise ValueError(f"There are less than 1 doctor(s) for day {day} in 'potential_charge_doctors'")

        for day, doctors_list in self.data.potential_cardiac_doctors.items():
            if day in self.data.weekdays and len(doctors_list) < 1:
                raise ValueError(f"There are less than 1 doctor(s) for day {day} in 'potential_cardiac_doctors'")

        # If it's exactly 1 doctor for both, check if they are different
        for day in self.data.weekdays:
            if len(self.data.potential_charge_doctors[day]) == 1 and len(self.data.potential_cardiac_doctors[day]) == 1:
                if self.data.potential_charge_doctors[day][0] == self.data.potential_cardiac_doctors[day][0]:
                    raise ValueError(
                        f"The same doctor, {self.data.potential_charge_doctors[day][0]}, "
                        f"is listed as the only option for both charge and cardiac on day {day}")

        # Check if the union of the doctors from both dictionaries for each day is >= 2
        for day in self.data.weekdays:
            unique_doctors = set(self.data.potential_charge_doctors[day]) | set(
                self.data.potential_cardiac_doctors[day])
            if len(unique_doctors) < 2:
                raise ValueError(
                    f"The union of doctors from both 'potential_charge_doctors' and 'potential_cardiac_doctors' for day {day} is less than 2")
