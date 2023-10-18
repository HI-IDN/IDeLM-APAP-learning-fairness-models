import datetime

import pandas as pd
from data.staff import Doctors


class DataHandler:
    # Week-days:
    days = ['MON', 'TUE', 'WED', 'THU', 'FRI']

    # Other sets of doctors:
    Whine = {}
    preassigned = {day: {} for day in days}
    charge_order_dict = {}
    potential_charge_doctors = {}
    potential_cardiac_doctors = {}
    call_and_late_call_doctors = {}
    Admin = {}
    orders = []
    preassigned_doctors = []
    whine_doctors = []

    def __init__(self, filepath, start_date=None, end_date=None):
        start_date = (datetime.date.today() - datetime.timedelta(days=7) if start_date is None
                      else datetime.datetime.strptime(start_date, '%Y-%m-%d').date())

        end_date = (datetime.date.today() + datetime.timedelta(days=7) if end_date is None
                    else datetime.datetime.strptime(end_date, '%Y-%m-%d').date())

        self.staff = Doctors(start_date=start_date, end_date=end_date)

        # if the file is a csv
        if filepath.endswith('.csv'):
            self.load_csv(filepath)
        else:
            raise ValueError('Filetype not supported.')

    def load_csv(self, filepath):
        """Load data from a CSV file."""
        df = pd.read_csv(filepath, header=0)

        # Select only the desired columns
        columns_to_use = ['Role'] + self.days
        df = df[columns_to_use]

        # Extract all anesthesiologists that still need to be assigned a fair workload per day:
        idx = list(range(0, 7)) + list(range(18, 20)) + list(range(20, 22)) + list(range(22, 36))

        for day in self.days:
            assigned_doctors = df[day].iloc[idx].dropna().values.tolist()
            self.Whine[day] = sorted(list(set(self.staff.everyone) - set(assigned_doctors)))

        # Extract preassigned doctors

        # Extracting the indices for 'Post CVCC', 'Call', and 'Late-call'
        start_row = df[df['Role'] == 'Post CVCC'].index[0]
        end_row = df[df['Role'] == 'call'].index[0]

        for day in self.days:
            order = 1
            for idx in range(start_row, end_row - 1):
                doctor = df[day].iloc[idx]
                if doctor and not pd.isna(doctor):  # If a doctor is assigned
                    self.preassigned[day][order] = doctor
                    order += 1

            # Adjust order for late-call and call doctors
            late_call_order = order + len(self.Whine[day])
            call_order = late_call_order + 1

            late_call_doctor = df.loc[df['Role'] == 'late', day].values[0]
            call_doctor = df.loc[df['Role'] == 'call', day].values[0]

            # Store the "late-call" and "call" doctors in the dictionary
            self.preassigned[day][late_call_order] = late_call_doctor
            self.preassigned[day][call_order] = call_doctor

            self.call_and_late_call_doctors[day] = [late_call_doctor, call_doctor]

            self.charge_order_dict[day] = len(self.Whine[day]) + len([o for o in self.preassigned[day]
                                                                      if o < len(self.Whine[day]) + 2])
            self.potential_charge_doctors[day] = sorted(
                list(set(self.Whine[day] + self.call_and_late_call_doctors[day]) & set(self.staff.charge_doctors)))

            self.potential_cardiac_doctors[day] = sorted(
                list(set(self.call_and_late_call_doctors[day]) & set(self.staff.cardiac_doctors))
            )

        # Extracts the admin doctors for each day.
        idx1 = df[df['Role'] == 'Admin 1'].index[0]
        idx2 = df[df['Role'] == 'Admin 2'].index[0]
        self.Admin = {day: [x if pd.notna(x) else '' for x in [df.loc[idx1, day], df.loc[idx2, day]]] for day in
                      self.days}

        # Extracting doctors from preassigned
        self.preassigned_doctors = [doctor for order_doctor_dict in self.preassigned.values() for doctor in
                                    order_doctor_dict.values()]

        # Extracting doctors from Whine
        self.whine_doctors = [doctor for whine_doctors_list in self.Whine.values() for doctor in whine_doctors_list]

        # Combining and creating a unique set of doctors
        self.doctors = set(self.preassigned_doctors + self.whine_doctors)

        # Redefining the set of orders based on the maximum order number in preassigned
        max_order = max([max(order_doctor_dict.keys()) for order_doctor_dict in self.preassigned.values()])
        self.orders = list(range(1, max_order + 1))

        # Roles, that match the order of the orders
        self.roles = {i: df['Role'].iloc[i + start_row] for i in self.orders}


if __name__ == '__main__':
    data = DataHandler('data/input.csv')
    print(data.Whine)
    print(data.preassigned)
    print(data.charge_order_dict)
    print(data.potential_charge_doctors)
    print(data.potential_cardiac_doctors)
    print(data.call_and_late_call_doctors)
    print(data.Admin)
    print(data.orders)
    print(data.roles)
    print(data.preassigned_doctors)
    print(data.whine_doctors)
    print(data.staff.everyone)
    print(data.staff.cardiac_doctors)
    print(data.staff.charge_doctors)
