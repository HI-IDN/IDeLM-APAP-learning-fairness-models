import sqlite3  # SQLite is a C library that provides a lightweight disk-based database
import glob  # Glob module is used to retrieve files/pathnames matching a specified pattern
import json  # JSON module is used to parse JSON files
import os  # OS module provides functions for interacting with the operating system
import csv  # CSV module is used to read/write CSV files
from datetime import datetime, timedelta
import argparse
from data.utils import custom_holidays, generate_dates, get_weekday_name
from data.schedule import DoctorSchedule
from gurobipy import GRB


def process_schedule_data(db_file, json_folder, staff_file):
    # Function to clean up the existing DB file
    def remove_db_file():
        if os.path.exists(db_file):
            os.remove(db_file)

    # Function to create database and tables
    def create_database():
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        # Create tables
        cursor.executescript("""
            CREATE TABLE schedule (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT UNIQUE,
                period_start TEXT,
                period_end TEXT,
                target_value FLOAT,
                workdays INTEGER,
                objective_total FLOAT,
                objective_equity INTEGER,
                objective_cardiac_charge INTEGER,
                objective_priority_charge INTEGER,
                num_constraints INTEGER, 
                num_variables INTEGER, 
                optimal BOOLEAN
            );

            CREATE TABLE doctors (
                id TEXT PRIMARY KEY,
                name TEXT,
                cardiac BOOLEAN,
                charge BOOLEAN
            );

            CREATE TABLE points (
                schedule_id INTEGER,
                doctor_id TEXT,
                fixed_points INTEGER,
                total_points INTEGER,
                cardiac INTEGER,
                charge INTEGER,
                days_working INTEGER,
                UNIQUE(doctor_id, schedule_id),
                FOREIGN KEY (schedule_id) REFERENCES schedule(id),
                FOREIGN KEY (doctor_id) REFERENCES doctors(id)
            );

            CREATE TABLE assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doctor_id TEXT,
                date TEXT,
                points INTEGER,
                role TEXT,
                schedule_id INTEGER,
                is_charge BOOLEAN,
                is_cardiac BOOLEAN,
                UNIQUE(doctor_id, date),
                FOREIGN KEY (schedule_id) REFERENCES schedule(id),
                FOREIGN KEY (doctor_id) REFERENCES doctors(id)
            );
            
            CREATE TABLE holidays (                
                date TEXT,
                description TEXT,
                UNIQUE(date)
            );
        """)
        conn.commit()
        return conn

    # Function to import doctors from CSV
    def import_doctors(cursor):
        with open(staff_file, 'r') as file:
            csv_reader = csv.reader(file)
            header = next(csv_reader)
            doctors = [(row[header.index('anst')], row[header.index('name')], row[header.index('diac')] == 'TRUE',
                        row[header.index('chrg')] == 'TRUE') for row in csv_reader]
            cursor.executemany("INSERT INTO doctors (id, name, cardiac, charge) VALUES (?, ?, ?, ?);", doctors)

    def import_holidays(cursor):
        for year in range(2018, datetime.now().year):
            holidays = custom_holidays(year)
            for date, holiday in holidays.items():
                cursor.execute("INSERT INTO holidays (date, description) VALUES (?, ?);", (date, holiday))

    def process_json_files(cursor, json_folder):
        # Function to parse date in ISO8601 format
        def parse_date(date_str):
            return datetime.fromisoformat(date_str).date()

        # Function to calculate workdays
        def calculate_workdays(days_list):
            return sum(1 for day in days_list if day == "Workday")

        def insert_schedule(period_start, period_end):
            # Extract schedule related data

            target_value = data['Solution']['Target']
            workdays = calculate_workdays(data['Day'])
            objective_equity = data['Solution']['Objective']['equity']
            objective_cardiac_charge = data['Solution']['Objective']['cardiac_charge']
            objective_priority_charge = data['Solution']['Objective']['priority_charge']
            objective_total = data['Solution']['Objective']['total']
            num_constraints = data['Solution']['Params']['Constraints']
            num_variables = data['Solution']['Params']['Variables']
            optimal = data['Solution']['Params']['Status'] == GRB.OPTIMAL

            # Insert into schedule table
            cursor.execute("""
                                INSERT INTO schedule (
                                    file_name, period_start, period_end, target_value, workdays,
                                    objective_total, objective_equity, objective_cardiac_charge, 
                                    objective_priority_charge, num_constraints, num_variables, optimal
                                )
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ? ,? ,? ,?);
                            """, (file_name, period_start, period_end, target_value, workdays,
                                  objective_total, objective_equity, objective_cardiac_charge,
                                  objective_priority_charge, num_constraints, num_variables, optimal))

            # Retrieve the last inserted schedule_id
            return cursor.lastrowid

        def insert_points(schedule_id):
            # Extract points for each doctor
            doctor_points_total = {doc: pts[0] for doc, pts in data['Solution']['Points'].items()}
            doctor_points_fixed = {doc: pts[1] for doc, pts in data['Solution']['Points'].items()}
            doctors = doctor_points_total.keys()

            # Extract doctors who have a charge role
            doctor_charge = {doctor: len([1 for chrg in data['Solution']['Charge'] if chrg == doctor]) for doctor in
                             doctors}

            # Extract doctors who have a cardiac role
            doctor_cardiac = {doctor: len([1 for diac in data['Solution']['Cardiac'] if diac == doctor]) for doctor in
                              doctors}

            days_working = {doctor: sum(
                assignment[0] == doctor for day in data['Solution']['Assignment'] for assignment in
                data['Solution']['Assignment'][day]) for doctor in doctors}

            # Insert data into the database
            for doctor in doctors:
                # Insert the data into SQLite
                cursor.execute(f"""
                        INSERT INTO points (schedule_id, doctor_id, total_points, fixed_points, 
                        cardiac, charge, days_working)
                        VALUES (? ,? ,? , ?, ?, ?, ?);
                    """, (schedule_id, doctor, doctor_points_total[doctor], doctor_points_fixed[doctor],
                          doctor == doctor_cardiac, doctor == doctor_charge, days_working[doctor]))

        def insert_assignments(schedule_id, period_start, days):

            for i, day in enumerate(days):
                date = period_start + timedelta(days=i)

                # Pre-calculate charge and cardiac statuses for the day
                charge_doctors = data['Solution']['Charge'][i]
                cardiac_doctors = data['Solution']['Cardiac'][i]

                # Pre-calculate roles for the day
                roles_for_day = {}
                for role in DoctorSchedule.TURN_ORDER:
                    role_data = data[role][i]
                    if isinstance(role_data, list):  # If there are multiple doctors for the role (e.g. Admin)
                        for doctor in role_data:
                            roles_for_day[doctor] = role
                    else:
                        roles_for_day[role_data] = role

                # Extract assignments for each doctor
                for doctor, points in data['Solution']['Assignment'][day]:

                    if not doctor or doctor == 'AD':
                        continue

                    is_charge = 1 if doctor == charge_doctors else 0
                    is_cardiac = 1 if doctor == cardiac_doctors else 0
                    role = roles_for_day[doctor]

                    # Insert into the database
                    cursor.execute("""
                            INSERT INTO assignments (doctor_id, date, points, schedule_id, is_charge, is_cardiac, role)
                            VALUES (?, ?, ?, ?, ?, ?, ?);
                        """, (doctor, date, points, schedule_id, is_charge, is_cardiac, role))

        # Loop through each JSON file in the folder
        for json_file_path in sorted(glob.glob(os.path.join(json_folder, '[0-9][0-9][0-9][0-9]-week[0-5][0-9].json'))):
            with open(json_file_path, 'r') as file:
                data = json.load(file)
                file_name = os.path.basename(json_file_path)
                print(file_name)

                period_start = parse_date(data['Period']['start'])
                period_end = parse_date(data['Period']['end'])
                days = [get_weekday_name(date) for date in generate_dates(period_start, period_end)]

                schedule_id = insert_schedule(period_start, period_end)
                insert_points(schedule_id)
                insert_assignments(schedule_id, period_start, days)

        # Remember to commit the changes
        conn.commit()

    # Main processing logic
    remove_db_file()
    conn = create_database()
    cursor = conn.cursor()
    import_doctors(cursor)
    import_holidays(cursor)
    process_json_files(cursor, json_folder)

    conn.close()


def main():
    # Create the parser
    parser = argparse.ArgumentParser(description="Process schedule data.")

    # Add arguments
    parser.add_argument("db_file", help="Path to the SQLite database file")
    parser.add_argument("json_folder", help="Path to the folder containing JSON files")
    parser.add_argument("--staff_file", help="Path to the staff CSV file", default="../data/staff.csv")

    # Parse the arguments
    args = parser.parse_args()

    # Process the schedule data
    process_schedule_data(args.db_file, args.json_folder, args.staff_file)


if __name__ == "__main__":
    main()
