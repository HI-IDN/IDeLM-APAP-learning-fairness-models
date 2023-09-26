import pandas as pd
import json
import argparse


def format_sheet(records, prev_month, this_month):
    current_day = 0
    next_month = {}
    month = None
    col_mapping = {
        records.columns[0]: 'Day',
        records.columns[1]: 'Shift',
        records.columns[2]: 'Call1st',
        records.columns[3]: 'Call2nd',
    }
    for index, row in records.iterrows():
        if not pd.isna(row[0]):
            records.drop(records.index[:index], inplace=True)
            break
        for col, value in row.items():
            if value == 'G1':
                col_mapping[col] = 'G1'
            elif value == '4G' or value == 'At Gillette':
                col_mapping[col] = '4G'
            elif value == 'CHC' or value == 'Children\'s Minnetonka':
                col_mapping[col] = 'CHC'
            elif value == 'CVCC':
                col_mapping[col] = 'CVCC'
            elif value == 'Sedation':
                col_mapping[col] = 'Sedation'
            elif value == 'Vacation':
                col_mapping[col] = 'Vacation'
            elif value == 'Requests':
                col_mapping[col] = 'Requests'

    # Rename columns using the mapping
    records.rename(columns=col_mapping, inplace=True)
    records = records.applymap(lambda x: x.strip() if isinstance(x, str) else x)

    for index, row in records.iterrows():
        day = int(row['Day'])
        if month is None:
            month = this_month if day < 15 else prev_month

        def transform_shift(shift):
            # Split the shift value into components (e.g. "Sunday AM" => ["Sunday", "AM"])
            components = shift.split()

            # Abbreviate the day to its first 3 letters
            day = components[0][:3]

            # If there's an AM/PM component, capitalize it
            if len(components) > 1:
                period = components[1].upper()
                return f"{day} {period}"
            else:
                return day

        shift = transform_shift(row[1])
        vacations = [item.strip() for item in row['Vacation'].split(',')] if not pd.isna(row['Vacation']) else []
        record = {
            'Call': {'1st': row['Call1st'].strip(), '2nd': row['Call2nd']},
            'Gillette': {
                'G1': row['G1'],
                '4G': [item.strip() for item in row['4G'].split(',')] if not pd.isna(row['4G']) else None
            },
            'CVCC': row['CVCC'] if not pd.isna(row['CVCC']) else None,
            'Vacation': [item for item in vacations if item != 'Adm'] if len(vacations) > 0 else None,
            'Admin': len([item for item in vacations if item == 'Adm']),
            'Requests': row['Requests'] if not pd.isna(row['Requests']) else None
        }
        if 'Sedation' in records.columns:
            record['Sedation'] = row['Sedation'] if not pd.isna(row['Sedation']) else None
        if 'CHC' in records.columns and not pd.isna(row['CHC']):
            record['West'] = {'CHC': row['CHC'] if not pd.isna(row['CHC']) else None}

        # Remove None values from record - they are not needed
        record = {k: v for k, v in record.items() if v is not None}

        if day < current_day:
            month = next_month if month is this_month else this_month

        if day not in month:
            month[day] = {}

        if shift not in month[day]:
            month[day][shift] = record
        else:
            raise Exception("Duplicate shift in same month")
        current_day = day

    return prev_month, this_month, next_month


def xls_to_json(filename):
    # Extract filename from path to get year and quarter
    filename_only = filename.split('/')[-1]
    year = int(filename_only.split('_')[0])
    quarter = int(filename_only.split('_')[1].split('q')[0])

    # Define the months for each quarter
    months_map = {
        1: ['Jan', 'Feb', 'Mar'],
        2: ['Apr', 'May', 'Jun'],
        3: ['Jul', 'Aug', 'Sep'],
        4: ['Oct', 'Nov', 'Dec']
    }

    # Load the Excel file
    xls = pd.ExcelFile(filename)
    data = {}
    if quarter == 1:
        data[year - 1] = {}
        data[year - 1][months_map[4][len(months_map[4]) - 1]] = {}
    data[year] = {}
    if quarter > 1:
        data[year][months_map[quarter - 1][len(months_map[quarter - 1]) - 1]] = {}
    for month in months_map[quarter]:
        data[year][month] = {}
    if quarter == 4:
        data[year + 1] = {}
        data[year + 1][months_map[1][0]] = {}
    else:
        data[year][months_map[quarter + 1][0]] = {}
    prev_month = {}
    this_month = {}

    # Assume each sheet corresponds to a month in the quarter
    for month_index, sheet_name in enumerate(xls.sheet_names):
        df = xls.parse(sheet_name)

        prev_month, this_month, next_month = format_sheet(df, prev_month, this_month)

        # concatenate this month and data['months'][month]
        month = months_map[quarter][month_index]
        data[year][month] = {**data[year][month], **this_month}

        # concatenate prev month and data['months'][month]
        if len(prev_month) > 0:
            prev_year = year
            if month_index - 1 >= 0:
                month = months_map[quarter][month_index - 1]
            else:
                # If it's the first month in the quarter
                if quarter == 1:
                    # If it's January, move to December of previous year
                    month = months_map[4][len(months_map[4]) - 1]
                    prev_year -= 1
                else:
                    # Move to the last month of the previous quarter
                    month = months_map[quarter - 1][len(months_map[quarter - 1]) - 1]
            data[prev_year][month] = {**data[prev_year][month], **prev_month}

        # concatenate next month and data['months'][month]
        if len(next_month) > 0:
            next_year = year
            if month_index + 1 < len(months_map[quarter]):
                # If it's not the last month in the quarter
                month = months_map[quarter][month_index + 1]
            else:
                # If it's the last month in the quarter
                if quarter == 4:
                    # If it's December, move to January of next year
                    month = months_map[1][0]
                    next_year += 1
                else:
                    # Move to the first month of the next quarter
                    month = months_map[quarter + 1][0]
            data[next_year][month] = {**data[next_year][month], **next_month}

        # reset this_month to next_month for next iteration
        prev_month = this_month
        this_month = next_month

    if quarter == 1:
        if len(data[year - 1]) == 0:
            data.pop(year - 1)
    else:
        if len(data[year][months_map[quarter - 1][len(months_map[quarter - 1]) - 1]]) == 0:
            data[year].pop(months_map[quarter - 1][len(months_map[quarter - 1]) - 1])
    if quarter == 4:
        if len(data[year + 1]) == 0:
            data.pop(year + 1)
    else:
        if len(data[year][months_map[quarter + 1][0]]) == 0:
            data[year].pop(months_map[quarter + 1][0])

    return json.dumps(data, indent=4)


# Set up the argument parser
parser = argparse.ArgumentParser(description='Convert xls to json')
parser.add_argument('filename', type=str, help='Path to the xls file to convert')
args = parser.parse_args()

json_data = xls_to_json(args.filename)
jsonfile = args.filename.replace('.xls', '.json')
with open(jsonfile, 'w') as outfile:
    outfile.write(json_data)
print("Wrote to file: " + jsonfile)
