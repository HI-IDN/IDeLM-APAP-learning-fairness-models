import gurobipy as gp
from gurobipy import GRB

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import numpy as np
import configparser
import os.path
import itertools

config = configparser.ConfigParser()
config.read('config.ini')

ADMIN_POINTS = 8
Wday = ['MON', 'TUE', 'WED', 'THU', 'FRI']

def read_google_sheet(config):
    sheet_name = config['GoogleSheet']['sheet_name']  # the name of the sheet you want to access
    document_id = config['GoogleSheet']['document_id']  # the long id in the sheets URL
    service_account_path = config['GoogleSheet']['service_account_path']  # path to your service account key json file

    local_file = f'../data/{sheet_name}.csv'
    if os.path.isfile(local_file):
        print(f'Local file found: {local_file}')
        df = pd.read_csv(local_file, index_col='Role').fillna('')
        return df

    print(f'Reading Google Sheet: {sheet_name} (id: {document_id})')
    # Authenticate and open GoogleSheets with the service account credentials
    creds = ServiceAccountCredentials.from_json_keyfile_name(service_account_path)
    client = gspread.authorize(creds)

    # Access your specific sheet within the document
    spreadsheet = client.open_by_key(document_id)
    worksheet = spreadsheet.worksheet(sheet_name)  # Access the sheet

    # Get data as a Pandas DataFrame
    df = pd.DataFrame(worksheet.get('A2:F40'), columns=worksheet.get('A1:F1')).fillna('')

    # Save the data locally
    df.to_csv(local_file, index=False)

    return df


def input_data(csv_file='../data/staff.csv'):
    # Read the CSV file
    df = pd.read_csv(csv_file)

    # The anesthetists are in the column 'anst'
    Anst = df['anst'].tolist()

    # Those who can do cardiac surgery are with TRUE values in 'diac'
    Diac = df[df['diac'] == True]['anst'].tolist()

    # The anesthetists that can be in charge are with TRUE values in 'chrg'
    Chrg = df[df['chrg'] == True]['anst'].tolist()


    return [Anst, Diac, Chrg]


def find_unassigned(df, Anst):
    """
    Find the unassigned anesthetists for each day of the week.

    Parameters:
    - df: DataFrame containing the assignments.
    - Anst: List of anesthetists.

    Returns:
    - Whine: Dictionary for each day of the week with anesthetists that are not assigned.
    """

    # Initialize dictionary with each day of the week having an empty list of unassigned anesthetists
    Whine = {key: [] for key in Wday}

    # Filter out rows with 'Whine' or 'Admin' in their index
    filtered_df = df[~df.index.str.contains('Whine|Admin')]
    whine_df = df[df.index.str.contains('Whine')]

    # Loop through columns (days)
    for day in filtered_df.columns:
        # Non-empty values are those that are assigned
        Assg = filtered_df[filtered_df[day] != ''][day]

        Unassg = sorted(list(set(Anst) - set(Assg.values)))

        # Determine the unassigned anesthetists and sort them
        Whine[day] = Unassg

    # Now we can safely remove the rows with 'West', 'Gill' or 'VAC' in their index in the local copy
    df = df[~df.index.str.contains('West|Gill|VAC')]

    df_pts = df.copy()

    # Iterate over days
    for day in df.columns:
        peel = 1

        # Update the df rows with the unassigned anesthetists as None
        for i in range(len(Whine[day])):
            if df.loc[whine_df.index[i], day] == '':
                df.loc[whine_df.index[i], day] = None

        # Iterate over roles for the current day
        for role, name in df[day].items():
            if name != '':
                if role.startswith('Admin'):
                    df_pts.loc[role, day] = ADMIN_POINTS
                else:
                    df_pts.loc[role, day] = peel
                    peel += 1

    return Whine, df, df_pts


def calculate_initial_points(df, Anst, df_pts):
    """
    Calculate the initial points for each individual based on their assignments.

    Parameters:
    - df: DataFrame containing the assignments.
    - Anst: List of individuals.
    - Whine: Dictionary containing individuals who are unavailable on specific days.

    Returns:
    - Pnts0: Dictionary of initial points for each individual.
    - Assg0: Dictionary indicating the number of pre-assignments for each individual.
    - Prep0: Dictionary indicating the number of persons assigned in slots 2,3,...,6 for each weekday.
    - Rank0: Dictionary containing rank values for each weekday.
    """

    tprPnts0 = {'AY': 20, 'BK': 2, 'CA': 13, 'CC': 0, 'CM': 0, 'DD': 0, 'DN': 0, 'ES': 19, 'FM': 0, 'JJ': 13, 'JM': 1,
                'JT': 0,
                'KC': 16, 'KK': 0, 'MA': 0, 'MC': 0, 'MI': 0, 'RR': 24, 'SK': 0, 'SL': 28, 'TI': 0, 'TT': 13}
    tprAssg0 = {'AY': 3, 'BK': 1, 'CA': 1, 'CC': 0, 'CM': 0, 'DD': 0, 'DN': 0, 'ES': 3, 'FM': 0, 'JJ': 1, 'JM': 1,
                'JT': 0,
                'KC': 2, 'KK': 0, 'MA': 0, 'MC': 0, 'MI': 0, 'RR': 1, 'SK': 0, 'SL': 2, 'TI': 0, 'TT': 1}
    tprPrep0 = {'MON': 1, 'TUE': 0, 'WED': 0, 'THU': 0, 'FRI': 0}

    Pnts0 = {key: 0 for key in Anst}
    Assg0 = {key: 0 for key in Anst}

    # The Rank is the first row of the whine part of the points table
    whine_df = df_pts[df_pts.index.str.contains('Whine')]
    Rank0 = whine_df.iloc[0].to_dict()

    # Handle pre/post roles
    pre_post_df = df[df.index.str.contains('Pre|Post')]
    Prep0 = {col: count - 4 for col, count in (pre_post_df != '').sum(axis=0).items()}

    # Iterate over the entire dataframe
    for col in df.columns:
        for row in df.index:
            name = df.at[row, col]
            if name:  # Checks for non-empty values
                Assg0[name] += int(df_pts.at[row, col])


    assert Prep0 == tprPrep0, f'{Prep0} != {tprPrep0}'
    #assert Pnts0 == tprPnts0, f'{Pnts0} != {tprPnts0}'
    # assert Assg0 == tprAssg0, f'{Assg0} != {tprAssg0}'
    print(Prep0)
    return Pnts0, Assg0, Prep0, Rank0


def check_missing_roles(df, Chrg, Diac, Whine):
    """
    Checks for missing charge and cardio roles for each day.

    :param df: DataFrame containing assignments.
    :param Chrg: Set/List of possible charge roles.
    :param Diac: Set/List of possible cardio roles.

    :return: Two dictionaries - missing charge and missing cardio for each day.
    """

    mCharge = {key: True for key in Wday}
    mCardio = {key: True for key in Wday}

    for i in range(1, 6):
        d = Wday[i - 1]
        # Check for charge
        for j in rows_mapping["late"]["indices"] + rows_mapping["call"]["indices"]:
            if df.iloc[j, i] in Chrg:
                mCharge[d] = False
            if df.iloc[j, i] in Diac:
                mCardio[d] = False

    onCall = {Wday[i - 1]: df.iloc[rows_mapping['call']['indices'][0], i] for i in range(1, 6)}
    onLate = {Wday[i - 1]: df.iloc[rows_mapping['late']['indices'][0], i] for i in range(1, 6)}

    # let's check if there is a missing charge or heart on any give day:
    for d in Wday:
        common = set(Chrg).intersection(set(Whine[d] + [onCall[d]] + [onLate[d]]))
        if (len(common) == 0):
            print("Missing a Charge on", d)
        common = set(Diac).intersection(set(Whine[d] + [onCall[d]] + [onLate[d]]))
        if (len(common) == 0):
            print("Missing a Cardio on", d)

    return mCharge, mCardio, onCall, onLate


def scan_whine_zone_for_pre_assigned(df):
    """
    Scan the Whine zone for pre-assigned roles. This function is used to block peel positions for special requests.

    :param df: DataFrame containing assignments.
    :param Wday: List of weekdays.

    :return: Dictionary with special peel positions for each anesthetist, day, and position.
    """

    SpPeel = {}

    for i in range(1, 6):
        for j in range(7, 18):
            if df.iloc[j, i] != '':
                a = df.iloc[j, i]
                d = Wday[i - 1]
                p = j - 3
                SpPeel[(a, d, p)] = True

    return SpPeel


def anesthesiologist_peel_assignment(df, Whine, Peel, Anst, Diac, Chrg, onCall, onLate, Pnts0, Assg0, Prep0,
                                     mCardio, mCharge, SpPeel):
    # Initialize model
    m = gp.Model("Anesthesiologist peel assignment problem (APAP)")

    # Filtered sets for compactness
    AWP = [(a, d, p) for d in Wday for a in Whine[d] for p in Peel[:(1 + len(Whine[d]))]]  # all possible assignments
    AdW = [(a, d) for d in Wday for a in Whine[d] + [onCall[d]] + [onLate[d]] if
           a in Diac]  # all possible cardio assignments
    AcW = [(a, d) for d in Wday for a in Whine[d] + [onCall[d]] + [onLate[d]] if
           a in Chrg]  # all possible charge assignments

    # Assigned position
    x = m.addVars(AWP, vtype="B")
    # Compute sum of points
    y = m.addVars(Anst, vtype="C")
    # Maximum points per any individual
    z1 = m.addVar()
    z2 = m.addVar()
    z3 = m.addVar()
    z4 = m.addVar()
    # Whos is the Cardio?
    h = m.addVars(AdW, vtype="B")
    # Whos is the Charge?
    c = m.addVars(AcW, vtype="B")
    zcha = m.addVar()  # max combined per a in Anst
    zch = m.addVars(Anst)

    # Those that have not been assigned to a slot yet must be assigned:
    m.addConstrs(gp.quicksum(x[a, d, p] for p in Peel[:(1 + len(Whine[d]))]) == 1 for d in Wday for a in Whine[d])

    # Can only assign one per peel per wday
    m.addConstrs(gp.quicksum(x[a, d, p] for a in Whine[d]) <= 1 for d in Wday for p in Peel[:(1 + len(Whine[d]))])

    # The approximate amount of points assigned to each Anesthetist
    m.addConstrs(
        gp.quicksum(x[a, d, p] * (p + Prep0[d]) for d in Wday for p in Peel if (a, d, p) in AWP) + Pnts0[a] == y[a] for
        a in Anst)

    # The maximum number (two layered press!)
    m.addConstrs(y[a] <= z1 for a in Anst if Assg0[a] < 4)
    m.addConstrs(y[a] <= z2 for a in Anst)
    m.addConstrs(y[a] >= z3 for a in Anst if Assg0[a] < 4)
    m.addConstrs(y[a] >= z4 for a in Anst)

    # now for the special conditions:
    # If we have a Cardio or Charge missing from any given day, then we should force them to be late out
    m.addConstrs(gp.quicksum(
        x[a, d, p] for a in Diac for p in Peel[(len(Whine[d]) - 1):(1 + len(Whine[d]))] if (a, d) in AdW) >= 1 for d in
                 Wday if mCardio[d])
    m.addConstrs(gp.quicksum(
        x[a, d, p] for a in Chrg for p in Peel[(len(Whine[d]) - 1):(1 + len(Whine[d]))] if (a, d) in AcW) >= 1 for d in
                 Wday if mCharge[d])

    # Tricky condition, minimizing the number of Cardio and Charge over the week, it works!
    m.addConstrs(gp.quicksum(c[a, d] for a in Whine[d] + [onCall[d]] + [onLate[d]] if a in Chrg) == 1 for d in Wday)
    m.addConstrs(gp.quicksum(h[a, d] for a in Whine[d] + [onCall[d]] + [onLate[d]] if a in Diac) == 1 for d in Wday)
    # The same person cannot take both roles:
    m.addConstrs(gp.quicksum(h[a, d] + c[a, d] for a in Chrg if (a, d) in AdW and (a, d) in AcW) <= 1 for d in Wday)
    # Now if we have decided the role then they must either be late or on call
    m.addConstrs(
        gp.quicksum(x[a, d, p] for p in Peel[(len(Whine[d]) - 1):(1 + len(Whine[d]))]) >= h[a, d] for (a, d) in AdW if
        (a != onCall[d]) and (a != onLate[d]))
    m.addConstrs(
        gp.quicksum(x[a, d, p] for p in Peel[(len(Whine[d]) - 1):(1 + len(Whine[d]))]) >= c[a, d] for (a, d) in AcW if
        (a != onCall[d]) and (a != onLate[d]))
    # now calculate the maximum number on Cardio or Charge
    m.addConstrs(
        gp.quicksum(h[a, d] for d in Wday if (a, d) in AdW) + gp.quicksum(c[a, d] for d in Wday if (a, d) in AcW) <=
        zch[a] for a in Chrg if a in Diac)
    m.addConstrs(gp.quicksum(c[a, d] for d in Wday if (a, d) in AcW) <= zch[a] for a in Chrg)
    m.addConstrs(gp.quicksum(h[a, d] for d in Wday if (a, d) in AdW) <= zch[a] for a in Diac)
    m.addConstrs(zch[a] <= zcha for a in Diac)

    # Only once in the end peel
    m.addConstrs(
        gp.quicksum(x[a, d, p] for d in Wday for p in Peel[len(Whine[d]) - 1:len(Whine[d])] if (a, d, p) in AWP) <= 1
        for a in Anst)

    # Special requests, fixed for Whine[d]
    m.addConstrs(x[a, d, p] == 1 for (a, d, p) in SpPeel.keys() if (a, d, p) in AWP)

    # minimize the maximum (worst case)
    m.setObjective(gp.quicksum(y[a] for a in Anst) + gp.quicksum(
        zch[a] for a in Anst) + 10000 * z1 + 10000 * z2 - 1 * z3 - 1 * z4 + 100 * zcha, GRB.MINIMIZE)
    # m.setObjective(gp.quicksum(y[a] for a in Anst) + 1000*z2 + gp.quicksum(zch[a] for a in Anst), GRB.MINIMIZE)

    # Optimize model
    m.optimize()

    # Display result:
    df_soln = df.copy()
    for i in range(1, 6):
        d = Wday[i - 1]
        for a in Whine[d]:
            for p in Peel[:(1 + len(Whine[d]))]:
                if x[a, d, p].X > 0.5:
                    # print(a,d,p)
                    df_soln.iloc[3 + p, i] = a
                    if (a in Diac):
                        if (h[a, d].X > 0.5):
                            df_soln.iloc[3 + p, i] = a + '*'
                    if (a in Chrg):
                        if (c[a, d].X > 0.5):
                            print("c[", a, d, "]=", c[a, d].X)
                            df_soln.iloc[3 + p, i] = a + '+'
        for j in [18, 19]:  # could have used here onCall on Late
            tmp = df.iloc[j, i]
            if (tmp in Chrg):
                if (c[tmp, d].X > 0.5):
                    df_soln.iloc[j, i] = df_soln.iloc[j, i] + '+'
            if (tmp in Diac):
                if (h[tmp, d].X > 0.5):
                    df_soln.iloc[j, i] = df_soln.iloc[j, i] + '*'

    # display the points per person:
    print("Points per person:")
    ppp = {}
    for a in Anst:
        if (int(y[a].X) > 0):
            print(int(y[a].X) + 0 * Pnts0[a], ":", a)
            ppp[a] = int(y[a].X + 0 * Pnts0[a])

    for (a, d) in AcW:
        if (int(c[a, d].X) > 0):
            print(a, " is on charge on ", d)
    for (a, d) in AdW:
        if (int(h[a, d].X) > 0):
            print(a, " is on cardio on ", d)
    print("max number of cardio+charge=", zcha.X)
    return df_soln, ppp


def print_points(df, df_pts):
    def format_cell(row, day):
        return f"{row[day]} ({df_pts.at[row.name, day]})" if row[day] != '' else ''

    formatted_df = df.copy()
    for day in df.columns:
        formatted_df[day] = df.apply(lambda row: format_cell(row, day), axis=1)

    print(formatted_df)

def main(verbose=True):
    df = read_google_sheet(config)
    Anst, Diac, Chrg = input_data()
    if verbose:
        print(f'Anesthetists: {Anst} (#{len(Anst)})')
        print(f'Cardiac anesthetists: {Diac} (#{len(Diac)})')
        print(f'Anesthetists that can be in charge: {Chrg} (#{len(Chrg)})')

    Whine, df, df_pts = find_unassigned(df, Anst)
    if verbose:
        print('Unassigned anesthetists:')
        for day in Whine:
            print(f'{day[:3]}:\t{Whine[day]}')

    if verbose:
        print_points(df, df_pts)

    Pnts0, Assg0, Prep0, Rank0 = calculate_initial_points(df, Anst, df_pts)
    if verbose:
        print('Initial points:')
        print({key: Pnts0[key] for key in Anst if Pnts0[key] > 0})

        print('Initial assignments:')
        print({key: Assg0[key] for key in Anst if Assg0[key] > 0})

        print('Initial pre-assignments:')
        print(Prep0)

        print('Initial ranks:')
        print(Rank0)
    assert 1 == 2
    mCharge, mCardio, onCall, onLate = check_missing_roles(df, Chrg, Diac, Whine)
    if verbose:
        print('Missing charge:')
        print(mCharge)
        print('Missing cardio:')
        print(mCardio)

    SpPeel = scan_whine_zone_for_pre_assigned(df)
    if verbose or True:
        print('Special peel positions:')
        print(SpPeel)

    df_soln, ppp = anesthesiologist_peel_assignment(df, Whine, Peel, Anst, Diac, Chrg, onCall, onLate, Pnts0,
                                                    Assg0, Prep0, mCardio, mCharge, SpPeel)
    print(df_soln)
    print(ppp)


main()
