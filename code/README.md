## Overview
The APAP system is designed to efficiently and fairly assign shifts and roles to anesthesiologists in a hospital setting, based on various factors like specializations, pre-assigned roles, and hospital policy.

## Problem Description
Anesthesiologists at a hospital have different roles and shifts, such as:
* Cardiac, 
* Charge, 
* Post call, 
* Post late, 
* Post CVCC, 
* Pre call, 
* Late, 
* Call. 

The objective is to ensure that roles and shifts are distributed fairly among anesthesiologists while adhering to certain constraints and ensuring specialized roles are filled appropriately.

## Code Explanation
### Data Import and Initialization:
**Google Sheets Integration**: The code fetches data directly from a specified Google Sheet which includes information about the anesthesiologists and their pre-assigned shifts.

**Anesthetists Details**: Anesthetists are represented with their initials in the code. Special roles and shifts are assigned to certain individuals based on their expertise.

### Model Creation:
The `gurobipy` package is used to formulate and solve the optimization problem.

#### Decision Variables:

* `x`: Represents whether an anesthetist `a` is assigned to a slot `p` on day `d`.
* `y`: Cumulative points assigned to each anesthetist `a` for their slots.
* `z1`, `z2`, `z3`, `z4`: Variables that determine the maximum and minimum points for all anesthetists.
* `h`: Decision on whether anesthetist `a` plays the role of Cardio on day `d`.
* `c`: Decision on whether anesthetist `a` is in charge on day `d`.

#### Constraints:

* Each anesthetist must be assigned one and only one slot for each day.
* For each slot on each day, only one anesthetist can be assigned.
* Points are calculated based on the slot they are assigned to.
* Constraints ensure that specialized roles like Cardio and Charge are assigned appropriately.
* Limits are placed on the number of times an anesthetist can be assigned to the Cardio or Charge role over the week.

#### Objective:

Minimize the maximum difference in points among all the anesthetists to ensure fairness.

### Post-processing:
After solving, the assignments can be written back to the Google Sheet or further processed as needed.

## Getting Started
### Prerequisites:
* Google Cloud authentication to access Google Sheets.
* Installation of packages listed in `requirements.txt` and the necessary authentication modules: 
   ```pip install -r requirements.txt ```

### Execution:
* Input the Google Sheets ID and Sheet name.
* Ensure that the Google Sheets data format matches the expected layout.
* Execute the code. Upon completion, assignments will be stored in the variable `x`.