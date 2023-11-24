#!/bin/bash

# The SQLite database file
DB_FILE=$1
JSON_FOLDER=$2

# Start with a clean database file
rm -f "$DB_FILE"

# Create a new SQLite database with the desired schema
sqlite3 "$DB_FILE" "
  CREATE TABLE IF NOT EXISTS schedule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name TEXT UNIQUE,
    period_start TEXT, -- Storing date as an ISO8601 string
    period_end TEXT,   -- Storing date as an ISO8601 string
    target_value INTEGER,
    workdays INTEGER,
    objective_total FLOAT,
    objective_equity INTEGER,
    objective_cardiac_charge INTEGER,
    objective_priority_charge INTEGER
  );

  CREATE TABLE IF NOT EXISTS doctors (
    id TEXT PRIMARY KEY,
    name TEXT,
    cardiac BOOLEAN,
    charge BOOLEAN
  );

  CREATE TABLE IF NOT EXISTS points (
    schedule_id INTEGER,
    doctor_id TEXT,
    fixed_points INTEGER,
    total_points INTEGER,
    cardiac INTEGER,
    charge INTEGER,
    UNIQUE(doctor_id, schedule_id),
    FOREIGN KEY (schedule_id) REFERENCES schedule(id),
    FOREIGN KEY (doctor_id) REFERENCES doctors(id)
  );

  CREATE TABLE IF NOT EXISTS assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doctor_id TEXT,
    date TEXT, -- Storing date as an ISO8601 string
    points TEXT,
    role TEXT,
    schedule_id INTEGER,
    is_charge BOOLEAN,
    is_cardiac BOOLEAN,
    UNIQUE(doctor_id, date),
    FOREIGN KEY (schedule_id) REFERENCES schedule(id),
    FOREIGN KEY (doctor_id) REFERENCES doctors(id)
  );"

# Import the doctors from the CSV file into the database
STAFF_FILE="../data/staff.csv"
awk -F, 'NR > 1 {OFS=","; print $1, $4, ($2=="TRUE"?"1":"0"), ($3=="TRUE"?"1":"0")}' $STAFF_FILE  | \
  sqlite3 "$DB_FILE" ".mode csv" ".import /dev/stdin doctors"

# Loop over each JSON file in the directory
for json_file in `find "$JSON_FOLDER" -name \*json -not -name \*-jon.json|sort`; do
  filename=$(basename "$json_file")
  echo $filename

  # Extract the period start and end, target value, and insert it into the Periods table
  period_start=$(jq -r '.Period.start' "$json_file")
  period_end=$(jq -r '.Period.end' "$json_file")
  target_value=$(jq -r '.Solution.Target' "$json_file")
  workdays=$(jq -r '.Day[]' "$json_file"|grep -c "Workday")
  objective_equity=$(jq -r '.Solution.Objective.equity' $json_file)
  objective_cardiac_charge=$(jq -r '.Solution.Objective.cardiac_charge' $json_file)
  objective_priority_charge=$(jq -r '.Solution.Objective.priority_charge' $json_file)
  objective_total=$(jq -r '.Solution.Objective.total' $json_file)


  schedule_id=$(sqlite3 "$DB_FILE" "
    INSERT INTO schedule (file_name, period_start, period_end, target_value, workdays,
    objective_total, objective_equity, objective_cardiac_charge, objective_priority_charge)
    VALUES ('$filename', '$period_start', '$period_end', $target_value, $workdays,
    $objective_total, ROUND($objective_equity), ROUND($objective_cardiac_charge), ROUND($objective_priority_charge)
    );")

  schedule_id=$(sqlite3 "$DB_FILE" "SELECT id FROM schedule WHERE file_name='$filename';")

  # Extract points for each doctor as "doctor_id=points"
  declare -A doctor_points_total=()
  declare -A doctor_points_fixed=()
  while IFS=" " read -r doctor total fixed; do
    doctor_points_total["$doctor"]=$total
    doctor_points_fixed["$doctor"]=$fixed
  done < <(jq -r '.Solution.Points | to_entries | .[] | "\(.key) \(.value[0]) \(.value[1])"' "$json_file")

  # Extract doctors who have a charge role
  declare -A doctor_charge=()
  for doctor in $(jq -r '.Solution.Charge[]' "$json_file"); do
    doctor_charge["$doctor"]=1
  done

  # Extract doctors who have a cardiac role
  declare -A doctor_cardiac=()
  for doctor in $(jq -r '.Solution.Cardiac[]' "$json_file"); do
    doctor_cardiac["$doctor"]=1
  done

  # Insert data into the database
  for doctor in "${!doctor_points_total[@]}"; do
    total_points=${doctor_points_total["$doctor"]:-0} # Default to 0 if not found in total array
    fixed_points=${doctor_points_fixed["$doctor"]:-0} # Default to 0 if not found in fixed array
    charge=${doctor_charge["$doctor"]:-0} # Default to 0 if not found in charge array
    cardiac=${doctor_cardiac["$doctor"]:-0} # Default to 0 if not found in cardiac array

    # Now insert the data into SQLite
    sqlite3 "$DB_FILE" "INSERT INTO points (schedule_id, doctor_id, total_points, fixed_points, cardiac, charge)
                        VALUES ($schedule_id, '$doctor', $total_points, $fixed_points, $cardiac, $charge);"
  done

  # Calculate dates based on period_start and day order
  for i in {0..6}; do
    date=$(date -I -d "$period_start + $i days")

    # Pre-calculate charge and cardiac statuses for the day
    charge_doctors=$(jq -r ".Solution.Charge[$i]" "$json_file")
    cardiac_doctors=$(jq -r ".Solution.Cardiac[$i]" "$json_file")

    # Pre-calculate roles for the day
    declare -A roles_for_day
    for special_role in OnCall OnLate PostCall PostHoliday PostLate PreCall Admin; do
      roles_for_day[$special_role]=$(jq -r ".${special_role}[$i]" "$json_file")
    done

    # Extract assignments for each doctor
    jq -r ".Solution.Assignment[$i][] | @csv" "$json_file" | while IFS=, read -r doctor points; do
      # Remove the extra double quotes from the doctor variable
      doctor=$(echo $doctor | sed 's/"//g')

      # Determine if the doctor is on charge or cardiac for this day
      is_charge=$(echo "$charge_doctors" | grep -cq "$doctor" && echo "1" || echo "0")
      is_cardiac=$(echo "$cardiac_doctors" | grep -cq "$doctor" && echo "1" || echo "0")

      # Identify the role of the doctor
      role='Whine'
      for special_role in "${!roles_for_day[@]}"; do
      if echo "${roles_for_day[$special_role]}" | grep -cq "$doctor"; then
        role=$special_role
        break
      fi
      done

      # Insert into the database
      sqlite3 "$DB_FILE" "
      INSERT INTO assignments (doctor_id, date, points, schedule_id, is_charge, is_cardiac, role)
      VALUES ('$doctor', '$date', $points, $schedule_id, $is_charge, $is_cardiac, '$role');"

    done
  done

done

echo "Data import complete."
