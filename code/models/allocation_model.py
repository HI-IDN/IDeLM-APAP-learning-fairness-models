import gurobipy as gp
from gurobipy import GRB
from gurobipy import Model, GRB


class AllocationModel:
    # Initialize the model
    m = Model("DoctorScheduling")

    def __init__(self, data):

        # Decision variables
        x = self.m.addVars(data.doctors, data.days, data.orders, vtype=GRB.BINARY)

        # Each doctor in Whine[day] is assigned to one order per day
        self.m.addConstrs((sum(x[doctor, day, order] for order in data.orders) == 1 for day in data.days for doctor in
                           data.Whine[day]))

        # Those pre-assigned can also be only at one place
        self.m.addConstrs((sum(x[doctor, day, order] for order in data.orders) == 1 for day in data.days for doctor in
                           list(data.preassigned[day].values())))

        # Each order on a given day is assigned to at most one doctor
        self.m.addConstrs((sum(x[doctor, day, order] for doctor in data.doctors) <= 1 for day in data.days for order in
                           data.orders))

        # Pre-assigned doctors
        for day, order_doctor_dict in data.preassigned.items():
            for order, doctor in order_doctor_dict.items():
                self.m.addConstr(x[doctor, day, order] == 1)

        # For each day, set x values to zero for doctors not scheduled
        for day in data.days:
            # Get the set of doctors who are scheduled for the day
            scheduled_doctors = set(data.Whine[day] + list(data.preassigned[day].values()))

            # Identify doctors who are not scheduled
            not_scheduled = [doctor for doctor in data.doctors if doctor not in scheduled_doctors]

            # Set x values to zero for these doctors
            self.m.addConstrs(x[doctor, day, order] == 0 for order in data.orders for doctor in not_scheduled)

            # Make sure that no doctor is assigned an order that goes beyond the "call", last one out
            self.m.addConstrs(x[doctor, day, order] == 0 for doctor in data.doctors for order in data.orders if
                              order > list(data.preassigned[day].keys())[-1])

        # Calculate the Total Order for Each Doctor
        total_order = {doctor: sum(order * x[doctor, day, order] for day in data.days for order in data.orders) for
                       doctor in data.doctors}

        # Adjust the total order for doctors with Admin duties
        q = 8  # the number of points given to admin roles, this is set to eight as default
        for day, admin_doctors in data.Admin.items():
            for doctor in admin_doctors:
                if doctor != '' and doctor in data.Whine[
                    day]:  # Check if there's a valid doctor name that is not an empty ''
                    total_order[doctor] += q  # When a doctor is in an admin position they are given q points

        # Introduce central_value variable, this is the target total_order value for all doctors
        self.central_value = self.m.addVar(vtype=GRB.INTEGER, name="central_value")

        ## Introduce y[doctor], lower_bound[doctor], and upper_bound[doctor] binary variables
        self.y = self.m.addVars(data.doctors, vtype=GRB.BINARY, name="y")

        # Large constant for big-M method
        M = len(data.days) * len(data.orders)

        # This constraint will force the indicator variable to be 1 if we hit the around the central_order
        self.m.addConstrs(total_order[doctor] - (self.central_value - 1) >= -M * (1 - self.y[doctor]) for doctor in
                          data.doctors)
        self.m.addConstrs((self.central_value + 1) - total_order[doctor] >= -M * (1 - self.y[doctor]) for doctor in
                          data.doctors)

        # Binary variable to indicate if a doctor is in charge for a particular day
        self.z = self.m.addVars(data.charge_doctors, data.days, vtype=GRB.BINARY, name="Charge Doctor: z")

        # Update the constraint to use potential_charge_doctors
        self.m.addConstrs((sum(z[doctor, day] for doctor in data.potential_charge_doctors[day]) == 1 for day in
                           data.days), name="one_in_charge")

        self.m.addConstrs((x[doctor, day, data.charge_order_dict[day]] >= self.z[doctor, day]
                           for day in data.days for doctor in data.charge_doctors if doctor in data.Whine[day]),
                          name="charge_order_constr")

        # Introduce a new binary variable w[doctor, day] to indicate if a doctor is the Cardiac doctor for the day
        self.w = self.m.addVars(data.cardiac_doctors, data.days, vtype=GRB.BINARY, name="Cardiac Doctor: w")

        # Each day should have exactly one Cardiac doctor
        self.m.addConstrs(
            (sum(self.w[doctor, day] for doctor in data.cardiac_doctors if doctor in data.call_and_late_call_doctors[
                day]) == 1 for day in data.days), name="one_cardiac")

        # A doctor cannot be both the Cardiac doctor and the Charge doctor on the same day
        common_doctors = set(data.charge_doctors) & set(data.cardiac_doctors)

        # A doctor cannot be both the Cardiac doctor and the Charge doctor on the same day
        self.m.addConstrs((self.w[doctor, day] + self.z[doctor, day] <= 1 for doctor in common_doctors for day in
                           data.days), name="cardiac_charge_conflict")

        # Calculate the total number of times each doctor is assigned the "Cardiac" role over the week
        total_in_cardiac = {
            doctor: sum(self.w[doctor, day] for day in data.days if doctor in data.call_and_late_call_doctors[day]) for
            doctor in data.cardiac_doctors}

        # Introduce a new variable to represent the maximum number of times any doctor is assigned the "Cardiac" role
        self.max_in_cardiac = self.m.addVar(name="max_in_cardiac")

        # Add constraints to ensure that the total number of times each doctor is assigned the "Cardiac" role is less
        # than or equal to max_in_cardiac
        self.m.addConstrs(total_in_cardiac[doctor] <= self.max_in_cardiac for doctor in data.cardiac_doctors)

        # Introduce a new variable to represent the maximum number of times any doctor is in charge
        self.max_in_charge = self.m.addVar(name="max_in_charge")

        # Calculate the total number of times each doctor is in charge over the week
        total_in_charge = {doctor: sum(self.z[doctor, day] for day in data.days) for doctor in data.charge_doctors}

        # Add constraints to ensure that the total number of times each doctor is in charge is less than or equal to
        # max_in_charge
        self.m.addConstrs(total_in_charge[doctor] <= self.max_in_charge for doctor in data.charge_doctors)

        # A doctor cannot be both the Cardiac doctor and the Charge doctor on the same day
        common_doctors = set(data.charge_doctors) & set(data.cardiac_doctors)
        self.m.addConstrs((self.w[doctor, day] + self.z[doctor, day] <= 1 for doctor in common_doctors for day in
                           data.days), name="cardiac_charge_conflict")

        # Add a variable that tells us the maximum that a doctor is both cardiac and charge over the week
        self.max_in_charge_cardiac = self.m.addVar(name="max_in_charge_cardiac")

        # Add constraints to ensure that the total number of times each doctor is in charge is less than or equal to
        # max_in_charge
        self.m.addConstrs(total_in_charge[doctor] + total_in_cardiac[doctor] <= self.max_in_charge_cardiac for doctor in
                          common_doctors)

        # Adjust the objective to minimize max_in_cardiac and max_in_charge while still prioritizing the equity objective
        alpha = 1  # Weight for the equity objective (most important)
        beta = 0.1  # Weight for the "In Charge" and "Cardiac" objectives
        gamma = 0.001
        obj1 = sum(self.y[doctor] for doctor in data.doctors)  # Equity objective
        obj2 = self.max_in_cardiac + self.max_in_charge + self.max_in_charge_cardiac  # Combined "In Charge" and
        # "Cardiac" objectives
        obj3 = sum(
            self.z[doctor, day] for day in data.days for doctor in data.charge_doctors if
            doctor in data.call_and_late_call_doctors[
                day])
        self.m.setObjective(alpha * obj1 - beta * obj2 + gamma * obj3, GRB.MAXIMIZE)

        # Ensure no doctor is "Charge" for two consecutive days
        for doctor in data.charge_doctors:
            for i in range(len(data.days) - 1):  # -1 because we're looking at pairs of days
                day1 = data.days[i]
                day2 = data.days[i + 1]
                self.m.addConstr(self.z[doctor, day1] + self.z[doctor, day2] <= 1,
                                 name=f"no_consecutive_charge_{doctor}_{day1}_{day2}")

        # Optimize the model
        self.m.optimize()

    def allocate(self):
        # Allocation logic here
        pass
